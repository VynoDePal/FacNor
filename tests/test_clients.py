from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.database import connect
from main import app


def create_user(database_path, email="clients@example.com"):
    with connect(database_path) as connection:
        return connection.execute(
            "INSERT INTO users (email, password_hash, full_name, company_name) VALUES (?, ?, ?, ?)",
            (email, "hash", "Client Owner", "Owner SAS"),
        ).lastrowid


def auth_headers(user_id, email="clients@example.com"):
    return {"Authorization": f"Bearer {create_access_token(user_id, email)}"}


B2B_PAYLOAD = {
    "client_type": "B2B",
    "name": "Entreprise SAS",
    "email": "contact@entreprise.test",
    "phone": "0102030405",
    "address_line1": "1 rue A",
    "postal_code": "75001",
    "city": "Paris",
    "country": "France",
    "siren": "123456789",
    "vat_number": "FR00123456789",
    "contact_full_name": "Alice Martin",
}

B2C_PAYLOAD = {
    "client_type": "B2C",
    "name": "Jean Dupont",
    "address_line1": "2 rue B",
    "postal_code": "69001",
    "city": "Lyon",
}


def test_authenticated_user_can_create_list_read_update_and_delete_clients(database_path):
    user_id = create_user(database_path)

    with TestClient(app) as client:
        create_response = client.post("/clients", json=B2B_PAYLOAD, headers=auth_headers(user_id))
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["client_type"] == "B2B"
        assert created["name"] == "Entreprise SAS"
        assert created["siren"] == "123456789"

        list_response = client.get("/clients", headers=auth_headers(user_id))
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()] == [created["id"]]

        read_response = client.get(f"/clients/{created['id']}", headers=auth_headers(user_id))
        assert read_response.status_code == 200
        assert read_response.json()["email"] == "contact@entreprise.test"

        update_response = client.patch(
            f"/clients/{created['id']}",
            json={"name": "Entreprise Modifiée", "contact_full_name": "Alice Durand"},
            headers=auth_headers(user_id),
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Entreprise Modifiée"
        assert update_response.json()["contact_full_name"] == "Alice Durand"

        delete_response = client.delete(f"/clients/{created['id']}", headers=auth_headers(user_id))
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        missing_response = client.get(f"/clients/{created['id']}", headers=auth_headers(user_id))
        assert missing_response.status_code == 404


def test_b2c_client_creation_and_cross_user_isolation(database_path):
    first_user_id = create_user(database_path, "first-client-owner@example.com")
    second_user_id = create_user(database_path, "second-client-owner@example.com")

    with TestClient(app) as client:
        create_response = client.post(
            "/clients",
            json=B2C_PAYLOAD,
            headers=auth_headers(first_user_id, "first-client-owner@example.com"),
        )
        assert create_response.status_code == 201
        client_id = create_response.json()["id"]
        assert create_response.json()["country"] == "France"
        assert create_response.json()["siren"] is None

        forbidden_read = client.get(
            f"/clients/{client_id}",
            headers=auth_headers(second_user_id, "second-client-owner@example.com"),
        )
        assert forbidden_read.status_code == 404

        second_list = client.get("/clients", headers=auth_headers(second_user_id, "second-client-owner@example.com"))
        assert second_list.status_code == 200
        assert second_list.json() == []


def test_clients_require_authentication_and_validate_business_rules(database_path):
    user_id = create_user(database_path)

    with TestClient(app) as client:
        unauthenticated = client.get("/clients")
        assert unauthenticated.status_code == 401

        invalid_b2b = client.post(
            "/clients",
            json={**B2B_PAYLOAD, "siren": None},
            headers=auth_headers(user_id),
        )
        assert invalid_b2b.status_code == 422

        invalid_b2c = client.post(
            "/clients",
            json={**B2C_PAYLOAD, "siren": "123456789"},
            headers=auth_headers(user_id),
        )
        assert invalid_b2c.status_code == 422


def test_duplicate_b2b_siren_is_rejected_per_user(database_path):
    user_id = create_user(database_path)

    with TestClient(app) as client:
        first_response = client.post("/clients", json=B2B_PAYLOAD, headers=auth_headers(user_id))
        duplicate_response = client.post("/clients", json=B2B_PAYLOAD, headers=auth_headers(user_id))

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
