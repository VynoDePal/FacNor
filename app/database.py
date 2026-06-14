from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT_DIR / "schema.sql"
DEFAULT_DATABASE_PATH = ROOT_DIR / "facnor.db"


def get_database_path() -> Path:
    return Path(os.getenv("FACNOR_DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))


def get_connection(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(database_path) if database_path is not None else get_database_path()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(database_path: str | Path | None = None) -> None:
    path = Path(database_path) if database_path is not None else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection(path) as connection:
        connection.executescript(schema)
