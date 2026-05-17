from contextlib import contextmanager

import duckdb

from app import config


@contextmanager
def get_db():
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn) -> None:
    """Create tables and run migrations on an open DuckDB connection."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            term       TEXT    NOT NULL,
            unit       INTEGER NOT NULL,
            mode       TEXT    NOT NULL,
            score      INTEGER NOT NULL,
            correct    INTEGER NOT NULL,
            ts         BIGINT  NOT NULL,
            time_taken INTEGER NOT NULL DEFAULT 0,
            expired    INTEGER NOT NULL DEFAULT 0
        )
    """)
    existing = {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'attempts'"
    ).fetchall()}
    if "time_taken" not in existing:
        conn.execute("ALTER TABLE attempts ADD COLUMN time_taken INTEGER DEFAULT 0")
    if "expired" not in existing:
        conn.execute("ALTER TABLE attempts ADD COLUMN expired INTEGER DEFAULT 0")


def init_db() -> None:
    with get_db() as conn:
        init_schema(conn)
