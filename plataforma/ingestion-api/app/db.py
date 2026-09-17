"""Base de datos: SQLite (una base en un archivo). Suficiente para la escala de la Pi.
Modo WAL para permitir lecturas mientras el consumidor MQTT escribe."""
import os
import sqlite3

# En Kubernetes esta ruta cae dentro del volumen persistente (PVC) montado en
# el pod - si el pod se reinicia, el archivo sigue estando ahi.
DB_PATH = os.getenv("DB_PATH", "/data/nubeultima.db")


def get_conn() -> sqlite3.Connection:
    """Abre una conexion nueva a la base. Se llama una vez por cada pedido
    HTTP o mensaje MQTT (no se comparte una sola conexion global) porque
    SQLite en modo WAL soporta bien muchas conexiones cortas concurrentes."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row  # permite leer filas como dict (fila["campo"])
    # WAL (Write-Ahead Logging): deja que se pueda LEER la base (la API REST)
    # mientras otro hilo la esta ESCRIBIENDO (el consumidor MQTT) sin que se
    # bloqueen entre si - clave porque ambas cosas pasan todo el tiempo.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    """Crea las tablas la primera vez que arranca el proceso. Los 'IF NOT
    EXISTS' hacen que sea seguro llamarla en cada arranque del pod sin borrar
    nada de lo que ya habia."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.executescript(
        """
        -- Cada lectura cruda que manda un dispositivo por MQTT.
        CREATE TABLE IF NOT EXISTS readings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            device_id TEXT    NOT NULL,
            zona      TEXT    NOT NULL,
            tipo      TEXT    NOT NULL,
            valor     REAL    NOT NULL,
            unidad    TEXT    NOT NULL
        );
        -- Indices para que /readings, /zonas y /devices no tengan que
        -- recorrer toda la tabla cada vez que se consultan.
        CREATE INDEX IF NOT EXISTS ix_readings_zt  ON readings(zona, tipo, ts);
        CREATE INDEX IF NOT EXISTS ix_readings_dev ON readings(device_id, ts);

        -- Cada anomalia que detectaron las reglas de rules.py.
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

        -- Tabla clave-valor donde los scripts externos de BaaS (backup.sh,
        -- restore-test.sh, corriendo en la Pi por fuera de este pod) dejan
        -- el estado del ultimo respaldo y de la ultima verificacion, para
        -- que el endpoint /baas los pueda leer y mostrar en el panel.
        CREATE TABLE IF NOT EXISTS baas_status (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()
