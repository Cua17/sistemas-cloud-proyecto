"""Base de datos: SQLite (una base en un archivo). Suficiente para la escala de la Pi.
Modo WAL para permitir lecturas mientras el consumidor MQTT escribe."""
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/data/nubeultima.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            device_id TEXT    NOT NULL,
            zona      TEXT    NOT NULL,
            tipo      TEXT    NOT NULL,
            valor     REAL    NOT NULL,
            unidad    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_readings_zt  ON readings(zona, tipo, ts);
        CREATE INDEX IF NOT EXISTS ix_readings_dev ON readings(device_id, ts);

        CREATE TABLE IF NOT EXISTS alerts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            device_id TEXT    NOT NULL,
            zona      TEXT    NOT NULL,
            tipo      TEXT    NOT NULL,
            regla     TEXT    NOT NULL,
            detalle   TEXT    NOT NULL,
            valor     REAL
        );
        CREATE INDEX IF NOT EXISTS ix_alerts_ts ON alerts(ts);

        CREATE TABLE IF NOT EXISTS baas_status (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()
