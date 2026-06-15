import sqlite3

from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.database import connect
from main import app


REGISTRATION_PAYLOAD = {
    "email": "invoice-user@facnor.test",
    "password": "MotDePasseSecurise123",
    "full_name": "Marie Martin",
    "company_name": "FacNor Demo",
}


def create_user_and_client(database_path, email="issuer@example.com"):
    with connect(database_path) as connection:
        user_id = connection.execute(
            "INSERT INTO users (email, password_hash, full_name, company_name) VALUES (?, ?, ?, ?)",
            (email, "hash", "Issuer", "Issuer SAS"),
        ).lastrowid
        client_id = connection.execute(
            """
            INSERT INTO clients (user_id, client_type, name, address_line1, postal_code, city)
            VALUES (?, 'B2C', 'Client', '1 rue Test', '44000', 'Nantes')
            """,
            (user_id,),
        ).lastrowid
    return user_id, client_id


def test_schema_creates_invoice_sequence_table(database_path):
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }

    assert "invoice_sequences" in tables


def test_invoice_numbers_are_unique_incremental_and_gapless(database_path):
    user_id, client_id = create_user_and_client(database_path)

    with TestClient(app) as client:
        invoices = [
            client.post(
                "/invoices",
                json={"client_id": client_id, "issue_date": f"2024-01-{day:02d}"},
                headers={"Authorization": f"Bearer {create_access_token(user_id, 'issuer@example.com')}"},
            )
            for day in range(1, 4)
        ]

    assert [response.status_code for response in invoices] == [201, 201, 201]
    assert [response.json()["invoice_number"] for response in invoices] == ["F-001", "F-002", "F-003"]

    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT last_number FROM invoice_sequences WHERE user_id = ? AND prefix = 'F'",
            (user_id,),
        ).fetchone()
    assert row["last_number"] == 3


def test_invoice_numbers_are_scoped_per_user(database_path):
    first_user_id, first_client_id = create_user_and_client(database_path, "first@example.com")
    second_user_id, second_client_id = create_user_and_client(database_path, "second@example.com")

    with TestClient(app) as client:
        first_response = client.post(
            "/invoices",
            json={"client_id": first_client_id, "issue_date": "2024-01-01"},
            headers={"Authorization": f"Bearer {create_access_token(first_user_id, 'first@example.com')}"},
        )
        second_response = client.post(
            "/invoices",
            json={"client_id": second_client_id, "issue_date": "2024-01-01"},
            headers={"Authorization": f"Bearer {create_access_token(second_user_id, 'second@example.com')}"},
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["invoice_number"] == "F-001"
    assert second_response.json()["invoice_number"] == "F-001"


def test_failed_invoice_creation_does_not_consume_number(database_path):
    user_id, client_id = create_user_and_client(database_path)

    token = create_access_token(user_id, "issuer@example.com")
    with TestClient(app) as client:
        missing_client_response = client.post(
            "/invoices",
            json={"client_id": client_id + 999, "issue_date": "2024-01-01"},
            headers={"Authorization": f"Bearer {token}"},
        )
        valid_response = client.post(
            "/invoices",
            json={"client_id": client_id, "issue_date": "2024-01-02"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert missing_client_response.status_code == 404
    assert valid_response.status_code == 201
    assert valid_response.json()["invoice_number"] == "F-001"


def test_authenticated_user_can_create_invoice_with_lines(database_path):
    with TestClient(app) as client:
        registration = client.post("/auth/register", json=REGISTRATION_PAYLOAD)
        token = registration.json()["access_token"]
        user_id = registration.json()["user"]["id"]

    with connect(database_path) as connection:
        client_id = connection.execute(
            """
            INSERT INTO clients (user_id, client_type, name, address_line1, postal_code, city)
            VALUES (?, 'B2C', 'Jean Dupont', '2 rue B', '69001', 'Lyon')
            """,
            (user_id,),
        ).lastrowid

    with TestClient(app) as client:
        response = client.post(
            "/invoices",
            json={
                "client_id": client_id,
                "issue_date": "2024-02-01",
                "lines": [
                    {
                        "description": "Prestation",
                        "quantity": "2",
                        "unit_price_excluding_tax": "100",
                        "vat_rate": "20",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["invoice_number"] == "F-001"
    assert payload["total_excluding_tax"] == "200.00"
    assert payload["total_tax"] == "40.00"
    assert payload["total_including_tax"] == "240.00"
    assert payload["lines"][0]["line_order"] == 1
