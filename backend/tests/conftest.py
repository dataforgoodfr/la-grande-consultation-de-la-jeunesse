import duckdb
import pytest
from fastapi.testclient import TestClient

from database.db_client import conn as real_client
from main import app


@pytest.fixture
def test_db():
    conn = duckdb.connect(":memory:")
    # TODO: add test db here
    yield conn
    conn.close()


@pytest.fixture
def client(test_db):
    # Override the real client to use the mocked one instead
    app.dependency_overrides[real_client] = lambda: test_db  # type: ignore
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
