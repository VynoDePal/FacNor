import sqlite3

import pytest


def test_schema_creates_required_tables(connection):
    table_names = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    assert {"users", "clients", "invoices", "invoice_lines"}.issubset(table_names)


def test_schema_enforces_foreign_keys(connection):
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO clients (user_id, name, address) VALUES (?, ?, ?)",
            (999, "Client inconnu", "1 rue inconnue"),
        )


def test_invoice_lines_cascade_when_invoice_deleted(connection):
    user_id = connection.execute(
        """
        INSERT INTO users (email, full_name, password_salt, password_hash, auth_token)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("user@example.com", "User Example", "salt", "hash", "token"),
    ).lastrowid
    client_id = connection.execute(
        "INSERT INTO clients (user_id, name, address) VALUES (?, ?, ?)",
        (user_id, "Client", "1 rue de Paris"),
    ).lastrowid
    invoice_id = connection.execute(
        """
        INSERT INTO invoices (user_id, client_id, invoice_number, issue_date)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, client_id, "FAC-001", "2025-01-01"),
    ).lastrowid
    connection.execute(
        """
        INSERT INTO invoice_lines (invoice_id, description, quantity, unit_price, line_total_excluding_tax)
        VALUES (?, ?, ?, ?, ?)
        """,
        (invoice_id, "Prestation", 1, 100, 100),
    )
    connection.commit()

    connection.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    connection.commit()

    count = connection.execute("SELECT COUNT(*) AS total FROM invoice_lines").fetchone()["total"]
    assert count == 0

