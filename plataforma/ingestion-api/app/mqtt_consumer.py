"""Consumidor MQTT: se suscribe al broker, valida cada lectura, la guarda en SQLite
y aplica las reglas de anomalia. Corre en un hilo de fondo dentro del proceso FastAPI."""
import collections
import json
import os
import threading
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt

from .db import get_conn
from .models import Reading
from .rules import evaluar

# Direccion del broker: dentro del cluster se resuelve por el nombre del Service
# de Kubernetes ("mqtt-broker"), no hace falta una IP fija.
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Historial en memoria, ultimos 10 valores por dispositivo. Vive solo mientras
# el proceso esta arriba (si el pod se reinicia, se pierde y arranca de nuevo).
# Lo usa la regla de fuga de agua para comparar contra la mediana reciente sin
# tener que ir a golpear la base de datos en cada lectura.
_hist: dict[str, collections.deque] = collections.defaultdict(
    lambda: collections.deque(maxlen=10)
)

# Contadores rapidos que expone /stats en main.py, para ver de un vistazo si
# el consumidor esta vivo y procesando (no reemplazan lo que ya esta en la DB).
_stats = {"recibidas": 0, "invalidas": 0, "alertas": 0}


def _on_connect(client, userdata, flags, rc):
    """Se llama una vez, apenas el cliente MQTT logra conectarse al broker.
    '#' es el comodin de MQTT: matchea todos los niveles del topic, asi que
    esta suscripcion cubre cualquier zona/tipo/dispositivo sin tener que
    listarlos a mano (ciudad/zona-1/agua/..., ciudad/zona-2/luz/..., etc)."""
    client.subscribe("ciudad/#")
    print(f"ingestion: conectado a MQTT ({rc}), suscrito a ciudad/#", flush=True)


def _on_message(client, userdata, msg):
    """Se llama por CADA mensaje que llega de cualquier dispositivo. Es el
    corazon del pipeline: valida -> guarda -> evalua reglas -> guarda alertas."""

    # 1) Validar. Lo que llega por MQTT es una fuente no confiable (podria
    # venir con un campo mal, un tipo invalido, etc). Reading (Pydantic) hace
    # de portero: si algo no cumple el esquema, tira excepcion y cortamos aca
    # sin llegar a tocar la base de datos.
    try:
        data = json.loads(msg.payload)
        r = Reading(**data).model_dump()
    except Exception as e:
        _stats["invalidas"] += 1
        print(f"ingestion: lectura invalida ({e})", flush=True)
        return

    conn = get_conn()
    try:
        # 2) Guardar la lectura cruda, siempre (sea o no anomala).
        conn.execute(
            "INSERT INTO readings(ts,device_id,zona,tipo,valor,unidad) VALUES(?,?,?,?,?,?)",
            (r["ts"], r["device_id"], r["zona"], r["tipo"], r["valor"], r["unidad"]),
        )

        # 3) Actualizar el historial en memoria de ESTE dispositivo (para la
        # regla de fuga de rules.py, que necesita ver los ultimos valores).
        _hist[r["device_id"]].append(r["valor"])

        # Corte de 10 min calculado en Python, en el MISMO formato (ISO-8601
        # con 'T') que se usa al guardar 'ts' un poco mas arriba. Importante:
        # comparar directo contra datetime('now','-10 minutes') de SQLite NO
        # sirve, porque esa funcion devuelve "YYYY-MM-DD HH:MM:SS" (con
        # espacio en vez de 'T') y la comparacion de texto entre los dos
        # formatos distintos daba siempre verdadero - la de-duplicacion
        # terminaba bloqueando la alerta de ese dispositivo+regla para
        # siempre despues del primer disparo, sin importar el tiempo real
        # que hubiera pasado. Por eso el corte se arma aca en Python, con el
        # mismo formato exacto que la columna, y se manda como parametro.
        hace_10min = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

        # 4) Evaluar las reglas de anomalia (rules.py) contra esta lectura +
        # el historial reciente. Puede devolver 0, 1 o varias alertas.
        for regla, detalle in evaluar(r, list(_hist[r["device_id"]])):
            # De-duplicacion: una alerta por episodio, no una por cada
            # lectura anomala. Si ya existe una alerta de este mismo
            # dispositivo+regla dentro de los ultimos 10 minutos, se ignora
            # (sin esto, una fuga que dura varios ciclos generaria una
            # alerta identica por cada lectura).
            ya = conn.execute(
                "SELECT 1 FROM alerts WHERE device_id=? AND regla=? "
                "AND ts >= ? LIMIT 1",
                (r["device_id"], regla, hace_10min),
            ).fetchone()
            if ya:
                continue  # ya hay una alerta reciente de este tipo, no se repite

            conn.execute(
                "INSERT INTO alerts(ts,device_id,zona,tipo,regla,detalle,valor) "
                "VALUES(?,?,?,?,?,?,?)",
                (r["ts"], r["device_id"], r["zona"], r["tipo"], regla, detalle, r["valor"]),
            )
            _stats["alertas"] += 1
            print(f"ingestion: ALERTA {regla} en {r['device_id']} - {detalle}", flush=True)

        # 5) Recien aca se confirma todo junto (la lectura + las alertas que
        # haya generado) en una sola transaccion.
        conn.commit()
        _stats["recibidas"] += 1
    finally:
        # Se cierra la conexion pase lo que pase (exito o excepcion), para no
        # ir acumulando conexiones SQLite abiertas mensaje tras mensaje.
        conn.close()


def start() -> None:
    """Arranca el cliente MQTT en un hilo de fondo aparte, para que FastAPI
    pueda seguir atendiendo pedidos HTTP en el hilo principal sin bloquearse
    esperando mensajes."""
    client = mqtt.Client(client_id="ingestion-api")
    client.on_connect = _on_connect
    client.on_message = _on_message
    # connect_async no bloquea: la conexion real pasa dentro de loop_forever,
    # que ademas reintenta solo si el broker todavia no esta levantado.
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
    threading.Thread(target=client.loop_forever, daemon=True, name="mqtt").start()
