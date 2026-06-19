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

BUSINESS_CLIENT_PAYLOAD = {
    "name": "Client Entreprise",
    "email": "contact@client.example",
    "client_type": "business",
    "siren": "987654321",
    "vat_number": "FR98765432100",
    "address": "2 avenue de Lyon, 69000 Lyon",
}

INDIVIDUAL_CLIENT_PAYLOAD = {
    "name": "Client Particulier",
    "email": "person@example.com",
    "client_type": "individual",
    "address": "3 rue de Lille, 59000 Lille",
}


def test_client_crud_supports_business_with_siren_and_vat() -> None:
    with client_api() as client:
        headers = _auth_headers(client)

        create_response = client.post("/api/clients", json=BUSINESS_CLIENT_PAYLOAD, headers=headers)
        assert create_response.status_code == 201
        created_client = create_response.json()
        client_id = created_client["id"]
        assert created_client["name"] == "Client Entreprise"
        assert created_client["client_type"] == "business"
        assert created_client["siren"] == "987654321"
        assert created_client["vat_number"] == "FR98765432100"

        read_response = client.get(f"/api/clients/{client_id}", headers=headers)
        assert read_response.status_code == 200
        assert read_response.json()["id"] == client_id

        update_response = client.put(
            f"/api/clients/{client_id}",
            json={"name": "Client Entreprise Renommé", "vat_number": "FR98765432199"},
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Client Entreprise Renommé"
        assert update_response.json()["vat_number"] == "FR98765432199"

        list_response = client.get("/api/clients", headers=headers)
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()] == [client_id]

        delete_response = client.delete(f"/api/clients/{client_id}", headers=headers)
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        missing_response = client.get(f"/api/clients/{client_id}", headers=headers)
        assert missing_response.status_code == 404


def test_client_api_supports_individual_clients_without_siren_or_vat() -> None:
    with client_api() as client:
        headers = _auth_headers(client)

        response = client.post("/api/clients", json=INDIVIDUAL_CLIENT_PAYLOAD, headers=headers)

        assert response.status_code == 201
        body = response.json()
        assert body["client_type"] == "individual"
        assert body["siren"] is None
        assert body["vat_number"] is None


def test_client_api_requires_authentication() -> None:
    with client_api() as client:
        response = client.post("/api/clients", json=BUSINESS_CLIENT_PAYLOAD)

        assert response.status_code == 401


def test_clients_are_isolated_by_authenticated_user() -> None:
    with client_api() as client:
        first_headers = _auth_headers(client, email="first@example.com")
        second_headers = _auth_headers(client, email="second@example.com")
        created = client.post("/api/clients", json=BUSINESS_CLIENT_PAYLOAD, headers=first_headers).json()

        list_response = client.get("/api/clients", headers=second_headers)
        read_response = client.get(f"/api/clients/{created['id']}", headers=second_headers)
        update_response = client.put(f"/api/clients/{created['id']}", json={"name": "Intrusion"}, headers=second_headers)
        delete_response = client.delete(f"/api/clients/{created['id']}", headers=second_headers)

        assert list_response.status_code == 200
        assert list_response.json() == []
        assert read_response.status_code == 404
        assert update_response.status_code == 404
        assert delete_response.status_code == 404


def test_client_payload_validates_siren_format() -> None:
    with client_api() as client:
        headers = _auth_headers(client)
        payload = BUSINESS_CLIENT_PAYLOAD | {"siren": "123"}

        response = client.post("/api/clients", json=payload, headers=headers)

        assert response.status_code == 422


class client_api:
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
