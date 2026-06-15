from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schema.sql"
DEFAULT_DATABASE_PATH = ROOT_DIR / "facnor.db"


def get_database_path() -> Path:
    return Path(os.getenv("FACNOR_DATABASE_PATH", DEFAULT_DATABASE_PATH)).resolve()


def connect(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(database_path).resolve() if database_path else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path: str | Path | None = None) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(database_path) as connection:
        connection.executescript(schema)
