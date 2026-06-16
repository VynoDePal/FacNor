from __future__ import annotations

import sqlite3

import pytest

from app.db import init_db


@pytest.fixture
def db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_db(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def sample_user_and_client(db: sqlite3.Connection) -> tuple[int, int]:
    user = db.execute(
        """
        INSERT INTO users (email, full_name, password_hash, company_name, siren, vat_number)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "marie@example.test",
            "Marie Dupont",
            "hash",
            "FacNor Conseil",
            "123456789",
            "FRAB123456789",
        ),
    )
    client = db.execute(
        """
        INSERT INTO clients (user_id, name, address, postal_code, city, siren, vat_number)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user.lastrowid,
            "Client SAS",
            "1 rue de Paris",
            "75001",
            "Paris",
            "987654321",
            "FRZZ987654321",
        ),
    )
    db.commit()
    return int(user.lastrowid), int(client.lastrowid)
