import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app, root_path="/api") as c:
        yield c
    app.dependency_overrides.clear()
