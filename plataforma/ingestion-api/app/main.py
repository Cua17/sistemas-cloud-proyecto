"""ingestion-api - microservicio de ingestion y consulta de telemetria.

- Se suscribe al broker MQTT y persiste las lecturas en SQLite (hilo de fondo).
- Expone una API REST para que el panel (SaaS) consulte datos y alertas.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI

from .db import get_conn, init_db
from .mqtt_consumer import _stats, start as start_mqtt


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Se corre una sola vez al arrancar el proceso, antes de aceptar el
    primer pedido HTTP: crea las tablas si no existen y prende el hilo de
    MQTT. El 'yield' es el momento en que la API ya queda arriba; todo lo que
    fuera despues correria al apagar el proceso (aca no hace falta nada)."""
    init_db()
    start_mqtt()
    yield


app = FastAPI(title="NubeUltima - ingestion-api", lifespan=lifespan)


def _desde(minutos: int) -> str:
    """Fecha/hora de hace N minutos, en el mismo formato ISO-8601 con el que
    se guarda 'ts' en la base - asi la comparacion 'ts >= ?' en SQL siempre
    compara texto con texto en el mismo formato (ver el comentario largo
    sobre este mismo tema en mqtt_consumer.py: mezclar este formato con el
    datetime('now', ...) propio de SQLite es lo que rompe la comparacion)."""
    return (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()


@app.get("/health")
def health():
    """Usado por el readinessProbe de Kubernetes: si esto responde 200, el
    pod se considera listo para recibir trafico."""
    return {"status": "ok"}


@app.get("/stats")
def stats():
    """Numeros generales para un vistazo rapido del estado del sistema."""
    conn = get_conn()
    n_r = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    n_a = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    n_d = conn.execute("SELECT COUNT(DISTINCT device_id) FROM readings").fetchone()[0]
    conn.close()
    return {"lecturas": n_r, "alertas": n_a, "dispositivos": n_d, "mqtt": _stats}


@app.get("/zonas")
def zonas():
    """Un resumen por zona de la ciudad: cuantos dispositivos tiene y cuantas
    alertas dispararon en los ultimos 15 minutos. La subconsulta de alertas
    corre una vez por cada zona que devuelve el GROUP BY de arriba."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT r.zona AS zona,
               COUNT(DISTINCT r.device_id) AS dispositivos,
               (SELECT COUNT(*) FROM alerts a
                 WHERE a.zona = r.zona
                   AND a.ts >= ?) AS alertas
        FROM readings r
        GROUP BY r.zona
        ORDER BY r.zona
        """,
        (_desde(15),),
    ).fetchall()
    conn.close()
    return [dict(x) for x in rows]


@app.get("/devices")
def devices():
    """Ultimo valor conocido de cada dispositivo. Las dos subconsultas
    'correlacionadas' (r2, r3) van dispositivo por dispositivo trayendo el
    dato mas reciente (ORDER BY ts DESC LIMIT 1), en vez de un JOIN comun que
    traeria todo el historial y habria que filtrar despues."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT device_id, zona, tipo,
               MAX(ts) AS ultima_lectura,
               (SELECT valor FROM readings r2
                 WHERE r2.device_id = r.device_id
                 ORDER BY ts DESC LIMIT 1) AS ultimo_valor,
               (SELECT unidad FROM readings r3
                 WHERE r3.device_id = r.device_id LIMIT 1) AS unidad
        FROM readings r
        GROUP BY device_id
        ORDER BY zona, tipo, device_id
        """
    ).fetchall()
    conn.close()
    return [dict(x) for x in rows]


@app.get("/readings")
def readings(zona: str | None = None, tipo: str | None = None, minutos: int = 60):
    """Lecturas crudas, filtrables por zona/tipo/ventana de tiempo. La consulta
    se arma en partes segun que filtros vengan en la URL, pero siempre con
    placeholders '?' (nunca metiendo el valor directo en el texto del SQL) -
    asi se evita inyeccion SQL aunque los parametros vengan del propio panel."""
    q = "SELECT ts,device_id,zona,tipo,valor,unidad FROM readings WHERE ts >= ?"
    args: list = [_desde(minutos)]
    if zona:
        q += " AND zona = ?"
        args.append(zona)
    if tipo:
        q += " AND tipo = ?"
        args.append(tipo)
    q += " ORDER BY ts DESC LIMIT 500"
    conn = get_conn()
    rows = conn.execute(q, args).fetchall()
    conn.close()
    return [dict(x) for x in rows]


@app.get("/baas")
def baas():
    """Estado del servicio de respaldo. No lo escribe este proceso: lo
    llenan los scripts externos de BaaS (backup.sh / restore-test.sh) que
    corren en la Pi por systemd timers, escribiendo directo en la tabla
    baas_status via 'kubectl exec'. Aca solo se lee y se devuelve como JSON."""
    import json as _json
    conn = get_conn()
    rows = conn.execute("SELECT k, v FROM baas_status").fetchall()
    conn.close()
    out = {}
    for r in rows:
        try:
            out[r["k"]] = _json.loads(r["v"])
        except Exception:
            out[r["k"]] = r["v"]
    return out


@app.get("/alerts")
def alerts(minutos: int = 120):
    """Alertas recientes, las mas nuevas primero."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts,device_id,zona,tipo,regla,detalle,valor FROM alerts "
        "WHERE ts >= ? ORDER BY ts DESC LIMIT 100",
        (_desde(minutos),),
    ).fetchall()
    conn.close()
    return [dict(x) for x in rows]
