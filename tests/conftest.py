from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import init_database
from app.main import app


@pytest.fixture()
def database_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "facnor_test.db"
    monkeypatch.setenv("FACNOR_DATABASE_PATH", str(path))
    init_database(path)
    return path


@pytest.fixture()
def client(database_path: Path) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
