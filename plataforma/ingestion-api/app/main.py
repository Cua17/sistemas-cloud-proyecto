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
    init_db()
    start_mqtt()
    yield


app = FastAPI(title="NubeUltima - ingestion-api", lifespan=lifespan)


def _desde(minutos: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    conn = get_conn()
    n_r = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    n_a = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    n_d = conn.execute("SELECT COUNT(DISTINCT device_id) FROM readings").fetchone()[0]
    conn.close()
    return {"lecturas": n_r, "alertas": n_a, "dispositivos": n_d, "mqtt": _stats}


@app.get("/zonas")
def zonas():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT r.zona AS zona,
               COUNT(DISTINCT r.device_id) AS dispositivos,
               (SELECT COUNT(*) FROM alerts a
                 WHERE a.zona = r.zona
                   AND a.ts >= datetime('now', '-2 hours')) AS alertas
        FROM readings r
        GROUP BY r.zona
        ORDER BY r.zona
        """
    ).fetchall()
    conn.close()
    return [dict(x) for x in rows]


@app.get("/devices")
def devices():
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


@app.get("/alerts")
def alerts(minutos: int = 120):
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts,device_id,zona,tipo,regla,detalle,valor FROM alerts "
        "WHERE ts >= ? ORDER BY ts DESC LIMIT 100",
        (_desde(minutos),),
    ).fetchall()
    conn.close()
    return [dict(x) for x in rows]
