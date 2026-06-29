from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
DEFAULT_DATABASE_PATH = BASE_DIR / "facnor.db"


def get_database_path() -> Path:
    return Path(os.getenv("FACNOR_DATABASE_PATH", DEFAULT_DATABASE_PATH))


def connect(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(database_path) if database_path is not None else get_database_path()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: str | Path | None = None) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
