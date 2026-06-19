from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.main import app

USER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "secure-password",
    "company_name": "FacNor SAS",
    "siren": "123456789",
    "vat_number": "FR12345678901",
    "address": "1 rue de Paris, 75000 Paris",
}

CLIENT_PAYLOAD = {
    "name": "Client Entreprise",
    "email": "contact@client.example",
    "client_type": "business",
    "siren": "987654321",
    "vat_number": "FR98765432100",
    "address": "2 avenue de Lyon, 69000 Lyon",
}

INVOICE_PAYLOAD = {
    "issue_date": "2025-01-15",
    "due_date": "2025-02-15",
    "items": [
        {
            "description": "Prestation de conseil",
            "quantity": "2.00",
            "unit_price_excluding_tax": "100.00",
            "vat_rate": "20.00",
        },
        {
            "description": "Abonnement",
            "quantity": "1.00",
            "unit_price_excluding_tax": "50.00",
            "vat_rate": "10.00",
        },
    ],
}


def test_invoice_crud_stores_lines_and_calculated_totals() -> None:
    with invoice_api() as client:
        headers = _auth_headers(client)
        client_id = _create_client(client, headers)

        create_response = client.post("/api/invoices", json=INVOICE_PAYLOAD | {"client_id": client_id}, headers=headers)
        assert create_response.status_code == 201
        created_invoice = create_response.json()
        invoice_id = created_invoice["id"]
        assert created_invoice["number"] == "0001"
        assert created_invoice["client_id"] == client_id
        assert created_invoice["total_excluding_tax"] == "250.00"
        assert created_invoice["total_tax"] == "45.00"
        assert created_invoice["total_including_tax"] == "295.00"
        assert [item["position"] for item in created_invoice["items"]] == [1, 2]
        assert created_invoice["items"][0]["total_including_tax"] == "240.00"

        read_response = client.get(f"/api/invoices/{invoice_id}", headers=headers)
        assert read_response.status_code == 200
        assert read_response.json()["items"][1]["description"] == "Abonnement"

        list_response = client.get("/api/invoices", headers=headers)
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()] == [invoice_id]

        update_response = client.put(
            f"/api/invoices/{invoice_id}",
            json={
                "status": "sent",
                "due_date": "2025-03-01",
                "items": [
                    {
                        "description": "Prestation ajustée",
                        "quantity": "3.00",
                        "unit_price_excluding_tax": "80.00",
                        "vat_rate": "20.00",
                    }
                ],
            },
            headers=headers,
        )
        assert update_response.status_code == 200
        updated_invoice = update_response.json()
        assert updated_invoice["number"] == "0001"
        assert updated_invoice["status"] == "sent"
        assert updated_invoice["due_date"] == "2025-03-01"
        assert updated_invoice["total_excluding_tax"] == "240.00"
        assert updated_invoice["total_tax"] == "48.00"
        assert updated_invoice["total_including_tax"] == "288.00"
        assert len(updated_invoice["items"]) == 1
        assert updated_invoice["items"][0]["position"] == 1

        delete_response = client.delete(f"/api/invoices/{invoice_id}", headers=headers)
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        missing_response = client.get(f"/api/invoices/{invoice_id}", headers=headers)
        assert missing_response.status_code == 404


def test_invoice_api_requires_existing_owned_client_and_authentication() -> None:
    with invoice_api() as client:
        headers = _auth_headers(client)
        other_headers = _auth_headers(client, email="other@example.com")
        client_id = _create_client(client, headers)

        unauthenticated_response = client.post("/api/invoices", json=INVOICE_PAYLOAD | {"client_id": client_id})
        assert unauthenticated_response.status_code == 401

        other_user_response = client.post("/api/invoices", json=INVOICE_PAYLOAD | {"client_id": client_id}, headers=other_headers)
        assert other_user_response.status_code == 404

        missing_client_response = client.post("/api/invoices", json=INVOICE_PAYLOAD | {"client_id": 999}, headers=headers)
        assert missing_client_response.status_code == 404


def test_invoices_are_isolated_by_authenticated_user() -> None:
    with invoice_api() as client:
        first_headers = _auth_headers(client, email="first@example.com")
        second_headers = _auth_headers(client, email="second@example.com")
        client_id = _create_client(client, first_headers)
        created = client.post("/api/invoices", json=INVOICE_PAYLOAD | {"client_id": client_id}, headers=first_headers).json()

        list_response = client.get("/api/invoices", headers=second_headers)
        read_response = client.get(f"/api/invoices/{created['id']}", headers=second_headers)
        update_response = client.put(f"/api/invoices/{created['id']}", json={"status": "paid"}, headers=second_headers)
        delete_response = client.delete(f"/api/invoices/{created['id']}", headers=second_headers)

        assert list_response.status_code == 200
        assert list_response.json() == []
        assert read_response.status_code == 404
        assert update_response.status_code == 404
        assert delete_response.status_code == 404


def test_invoice_payload_requires_at_least_one_line() -> None:
    with invoice_api() as client:
        headers = _auth_headers(client)
        client_id = _create_client(client, headers)

        response = client.post("/api/invoices", json={"client_id": client_id, "items": []}, headers=headers)

        assert response.status_code == 422


class invoice_api:
    def __enter__(self) -> TestClient:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def override_get_db() -> Generator[Session, None, None]:
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        return self.client

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        app.dependency_overrides.clear()


def _auth_headers(client: TestClient, email: str = USER_PAYLOAD["email"]) -> dict[str, str]:
    payload = USER_PAYLOAD | {"email": email}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_client(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/api/clients", json=CLIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    return int(response.json()["id"])
