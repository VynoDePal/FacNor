from __future__ import annotations

import sqlite3

import pytest

from app.db import create_invoice


def test_schema_creates_required_tables(db: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    assert {"users", "clients", "invoice_sequences", "invoices", "invoice_lines"} <= tables


def test_clients_require_existing_user_and_valid_siren(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO clients (user_id, name, address, postal_code, city)
            VALUES (999, 'Client orphelin', '1 rue A', '75001', 'Paris')
            """
        )

    db.execute(
        "INSERT INTO users (email, full_name, password_hash) VALUES (?, ?, ?)",
        ("user@example.test", "User", "hash"),
    )
    user_id = db.execute("SELECT id FROM users").fetchone()["id"]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO clients (user_id, name, address, postal_code, city, siren)
            VALUES (?, 'Client invalide', '1 rue B', '75002', 'Paris', 'ABC')
            """,
            (user_id,),
        )


def test_create_invoice_assigns_sequential_numbers_and_totals(
    db: sqlite3.Connection, sample_user_and_client: tuple[int, int]
) -> None:
    user_id, client_id = sample_user_and_client

    first = create_invoice(
        db,
        user_id=user_id,
        client_id=client_id,
        lines=[
            {
                "description": "Prestation conseil",
                "quantity": 2,
                "unit_price_excluding_tax": 10000,
                "vat_rate": 20,
            },
            {
                "description": "Frais administratifs",
                "quantity": 1,
                "unit_price_excluding_tax": 5000,
                "vat_rate": 10,
            },
        ],
    )
    second = create_invoice(
        db,
        user_id=user_id,
        client_id=client_id,
        lines=[
            {
                "description": "Suivi",
                "quantity": 1,
                "unit_price_excluding_tax": 10000,
                "vat_rate": 20,
            }
        ],
    )

    assert first["sequence_number"] == 1
    assert first["invoice_number"] == "FAC-000001"
    assert first["total_excluding_tax"] == 25000
    assert first["total_tax"] == 4500
    assert first["total_including_tax"] == 29500
    assert second["sequence_number"] == 2
    assert second["invoice_number"] == "FAC-000002"

    lines_count = db.execute("SELECT COUNT(*) AS count FROM invoice_lines").fetchone()["count"]
    assert lines_count == 3


def test_invoice_numbers_are_unique_and_strictly_increasing(
    db: sqlite3.Connection, sample_user_and_client: tuple[int, int]
) -> None:
    user_id, client_id = sample_user_and_client

    invoices = [
        create_invoice(
            db,
            user_id=user_id,
            client_id=client_id,
            lines=[
                {
                    "description": f"Prestation {index}",
                    "quantity": 1,
                    "unit_price_excluding_tax": 1000,
                    "vat_rate": 20,
                }
            ],
        )
        for index in range(5)
    ]

    sequence_numbers = [invoice["sequence_number"] for invoice in invoices]
    invoice_numbers = [invoice["invoice_number"] for invoice in invoices]

    assert sequence_numbers == [1, 2, 3, 4, 5]
    assert invoice_numbers == ["FAC-000001", "FAC-000002", "FAC-000003", "FAC-000004", "FAC-000005"]
    assert len(set(invoice_numbers)) == len(invoice_numbers)
    assert db.execute("SELECT next_number FROM invoice_sequences WHERE user_id = ?", (user_id,)).fetchone()[
        "next_number"
    ] == 6


def test_invoice_number_uniqueness_is_enforced_by_schema(
    db: sqlite3.Connection, sample_user_and_client: tuple[int, int]
) -> None:
    user_id, client_id = sample_user_and_client
    first = create_invoice(
        db,
        user_id=user_id,
        client_id=client_id,
        lines=[
            {
                "description": "Prestation initiale",
                "quantity": 1,
                "unit_price_excluding_tax": 1000,
                "vat_rate": 20,
            }
        ],
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO invoices (user_id, client_id, sequence_number, invoice_number)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, client_id, first["sequence_number"], "FAC-999999"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO invoices (user_id, client_id, sequence_number, invoice_number)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, client_id, 999999, first["invoice_number"]),
        )

