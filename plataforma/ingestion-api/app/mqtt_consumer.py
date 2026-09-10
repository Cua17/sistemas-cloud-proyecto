"""Consumidor MQTT: se suscribe al broker, valida cada lectura, la guarda en SQLite
y aplica las reglas de anomalia. Corre en un hilo de fondo dentro del proceso FastAPI."""
import collections
import json
import os
import threading

import paho.mqtt.client as mqtt

from .db import get_conn
from .models import Reading
from .rules import evaluar

MQTT_HOST = os.getenv("MQTT_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# historial en memoria: ultimos N valores por dispositivo (para la regla de fuga)
_hist: dict[str, collections.deque] = collections.defaultdict(
    lambda: collections.deque(maxlen=10)
)
_stats = {"recibidas": 0, "invalidas": 0, "alertas": 0}


def _on_connect(client, userdata, flags, rc):
    client.subscribe("ciudad/#")
    print(f"ingestion: conectado a MQTT ({rc}), suscrito a ciudad/#", flush=True)


def _on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        r = Reading(**data).model_dump()
    except Exception as e:
        _stats["invalidas"] += 1
        print(f"ingestion: lectura invalida ({e})", flush=True)
        return

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO readings(ts,device_id,zona,tipo,valor,unidad) VALUES(?,?,?,?,?,?)",
            (r["ts"], r["device_id"], r["zona"], r["tipo"], r["valor"], r["unidad"]),
        )
        _hist[r["device_id"]].append(r["valor"])
        for regla, detalle in evaluar(r, list(_hist[r["device_id"]])):
            # De-duplicacion: una alerta por episodio. Si ya hay una del mismo
            # dispositivo y regla en los ultimos 10 min, no se repite.
            ya = conn.execute(
                "SELECT 1 FROM alerts WHERE device_id=? AND regla=? "
                "AND ts >= datetime('now','-10 minutes') LIMIT 1",
                (r["device_id"], regla),
            ).fetchone()
            if ya:
                continue
            conn.execute(
                "INSERT INTO alerts(ts,device_id,zona,tipo,regla,detalle,valor) "
                "VALUES(?,?,?,?,?,?,?)",
                (r["ts"], r["device_id"], r["zona"], r["tipo"], regla, detalle, r["valor"]),
            )
            _stats["alertas"] += 1
            print(f"ingestion: ALERTA {regla} en {r['device_id']} - {detalle}", flush=True)
        conn.commit()
        _stats["recibidas"] += 1
    finally:
        conn.close()


def start() -> None:
    client = mqtt.Client(client_id="ingestion-api")
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
    threading.Thread(target=client.loop_forever, daemon=True, name="mqtt").start()
