import os
import sqlite3
from flask import g

# Soporte opcional para PostgreSQL (usado en Render)
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    psycopg2_extras = None
    HAS_PSYCOPG2 = False

DB_FILENAME = "egresados.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_FILENAME)
DEFAULT_TIMEOUT = 10.0  # segundos

# Si existe DATABASE_URL, usaremos Postgres
DATABASE_URL = os.environ.get('DATABASE_URL')


def _sqlite_connection():
    conn = sqlite3.connect(DB_PATH, timeout=DEFAULT_TIMEOUT, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Optimización para concurrencia y espera en locks
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def _postgres_connection():
    # Verificar que el adaptador esté disponible
    if not HAS_PSYCOPG2:
        raise ImportError("psycopg2 no está instalado. Instálalo con: python -m pip install psycopg2-binary")
    # Usar RealDictCursor para obtener filas como dicts
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def get_connection():
    """Devuelve una nueva conexión al motor apropiado (SQLite o Postgres)."""
    if DATABASE_URL:
        return _postgres_connection()
    return _sqlite_connection()


def get_db():
    """Devuelve una conexión por contexto de Flask (almacenada en `g`)."""
    if 'db_conn' not in g:
        g.db_conn = get_connection()
    return g.db_conn


def close_db(e=None):
    """Cierra la conexión almacenada en `g` si existe."""
    conn = g.pop('db_conn', None)
    if conn is not None:
        conn.close()


def init_db():
    """Crea la tabla `egresados` si no existe (adapta SQL según motor)."""
    if DATABASE_URL:
        # PostgreSQL
        conn = _postgres_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS egresados (
                matricula TEXT PRIMARY KEY CHECK (char_length(matricula)=8 AND matricula ~ '^[0-9]{8}$'),
                nombre_completo TEXT NOT NULL,
                carrera TEXT,
                generacion TEXT,
                estatus TEXT CHECK (estatus IN ('Egresado', 'En seguimiento', 'Titulado')),
                domicilio TEXT,
                genero TEXT,
                telefono TEXT,
                correo_electronico TEXT
            );
            """
        )
        conn.commit()
        cur.close()
        conn.close()
    else:
        # SQLite
        conn = _sqlite_connection()
        c = conn.cursor()
        # Asegurar modo WAL
        c.execute("PRAGMA journal_mode = WAL;")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS egresados (
                matricula TEXT PRIMARY KEY CHECK (length(matricula)=8 AND matricula GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
                nombre_completo TEXT NOT NULL,
                carrera TEXT,
                generacion TEXT,
                estatus TEXT CHECK (estatus IN ('Egresado', 'En seguimiento', 'Titulado')),
                domicilio TEXT,
                genero TEXT,
                telefono TEXT,
                correo_electronico TEXT
            );
            """
        )

        conn.commit()
        conn.close()


if __name__ == "__main__":
    init_db()
    if DATABASE_URL:
        print("Base de datos PostgreSQL verificada (DATABASE_URL)")
    else:
        print(f"Base de datos SQLite creada o verificada en: {DB_PATH}")