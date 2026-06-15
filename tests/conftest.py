import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database import init_db


@pytest.fixture()
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "facnor_test.db"
    monkeypatch.setenv("FACNOR_DATABASE_PATH", str(path))
    init_db(path)
    return path
