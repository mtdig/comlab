import duckdb
import pytest

import app.config as cfg
from app.database import init_schema


@pytest.fixture
def db_conn():
    """In-memory DuckDB connection with the schema pre-created."""
    conn = duckdb.connect(":memory:")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """FastAPI TestClient backed by a fresh temp-file DuckDB for each test."""
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "test.duckdb")
    from main import app as fastapi_app
    from fastapi.testclient import TestClient
    with TestClient(fastapi_app) as c:
        yield c
