from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import connect, initialize_database
from app.main import app


@pytest.fixture()
def database_path(tmp_path):
    path = tmp_path / "facnor_test.db"
    initialize_database(path)
    return path


@pytest.fixture()
def connection(database_path):
    connection = connect(database_path)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture()
def client(database_path, monkeypatch):
    monkeypatch.setenv("FACNOR_DATABASE_PATH", str(database_path))
    with TestClient(app) as test_client:
        yield test_client
