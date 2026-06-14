import sqlite3
from pathlib import Path

from app.database import init_database


def test_init_database_creates_required_tables(database_path: Path) -> None:
    expected_tables = {"users", "clients", "invoices", "invoice_items"}

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert expected_tables.issubset(table_names)


def test_schema_defines_expected_foreign_keys(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        clients_foreign_keys = connection.execute("PRAGMA foreign_key_list(clients)").fetchall()
        invoices_foreign_keys = connection.execute("PRAGMA foreign_key_list(invoices)").fetchall()
        invoice_items_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(invoice_items)"
        ).fetchall()

    assert ("users", "user_id", "id", "CASCADE") in {
        (row[2], row[3], row[4], row[6]) for row in clients_foreign_keys
    }
    assert {
        ("users", "user_id", "id", "CASCADE"),
        ("clients", "client_id", "id", "RESTRICT"),
    }.issubset({(row[2], row[3], row[4], row[6]) for row in invoices_foreign_keys})
    assert ("invoices", "invoice_id", "id", "CASCADE") in {
        (row[2], row[3], row[4], row[6]) for row in invoice_items_foreign_keys
    }


def test_schema_allows_creating_invoice_with_items(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.execute(
            """
            INSERT INTO users (email, full_name, hashed_password)
            VALUES (?, ?, ?)
            """,
            ("ada@example.com", "Ada Lovelace", "hashed-password"),
        )
        user_id = cursor.lastrowid
        cursor = connection.execute(
            """
            INSERT INTO clients (user_id, name, client_type, email, address)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, "Client SAS", "company", "client@example.com", "1 rue de Paris"),
        )
        client_id = cursor.lastrowid
        cursor = connection.execute(
            """
            INSERT INTO invoices (
                user_id, client_id, invoice_number, issue_date,
                total_excluding_tax, total_vat, total_including_tax
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, client_id, "FAC-2024-0001", "2024-01-15", 100, 20, 120),
        )
        invoice_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO invoice_items (
                invoice_id, description, quantity, unit_price_excluding_tax,
                vat_rate, line_total_excluding_tax, line_total_vat,
                line_total_including_tax
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (invoice_id, "Prestation", 2, 50, 20, 100, 20, 120),
        )
        result = connection.execute("SELECT COUNT(*) FROM invoice_items").fetchone()

    assert result == (1,)


def test_init_database_is_idempotent(database_path: Path) -> None:
    init_database(database_path)

    with sqlite3.connect(database_path) as connection:
        result = connection.execute("SELECT COUNT(*) FROM clients").fetchone()

    assert result == (0,)
