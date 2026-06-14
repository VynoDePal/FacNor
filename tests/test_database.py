import sqlite3
from pathlib import Path

from app.database import init_database


def test_init_database_creates_required_tables(database_path: Path) -> None:
    expected_tables = {"users", "clients", "invoices", "invoice_lines"}

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert expected_tables.issubset(table_names)


def test_init_database_is_idempotent(database_path: Path) -> None:
    init_database(database_path)

    with sqlite3.connect(database_path) as connection:
        result = connection.execute("SELECT COUNT(*) FROM clients").fetchone()

    assert result == (0,)
