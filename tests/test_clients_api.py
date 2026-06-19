from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_read_update_delete_particulier(client: TestClient) -> None:
    create_response = client.post(
        "/api/clients",
        json={
            "type": "Particulier",
            "name": "Jean Dupont",
            "email": "jean.dupont@example.com",
            "address": "1 rue de Paris, 75001 Paris",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] > 0
    assert created["name"] == "Jean Dupont"

    client_id = created["id"]
    read_response = client.get(f"/api/clients/{client_id}")
    assert read_response.status_code == 200
    assert read_response.json()["email"] == "jean.dupont@example.com"

    update_response = client.put(f"/api/clients/{client_id}", json={"name": "Jean Martin"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Jean Martin"

    delete_response = client.delete(f"/api/clients/{client_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/clients/{client_id}").status_code == 404


def test_company_requires_siren_or_vat_number(client: TestClient) -> None:
    response = client.post(
        "/api/clients",
        json={"type": "Entreprise", "name": "ACME SAS"},
    )

    assert response.status_code == 422
    assert "SIREN ou un numéro de TVA" in response.text


def test_company_can_be_created_with_siren(client: TestClient) -> None:
    response = client.post(
        "/api/clients",
        json={"type": "Entreprise", "name": "ACME SAS", "siren": "123456789"},
    )

    assert response.status_code == 201
    assert response.json()["siren"] == "123456789"


def test_update_cannot_turn_client_into_company_without_identity(client: TestClient) -> None:
    created = client.post(
        "/api/clients",
        json={"type": "Particulier", "name": "Jean Dupont"},
    ).json()

    response = client.put(f"/api/clients/{created['id']}", json={"type": "Entreprise"})

    assert response.status_code == 422
    assert "SIREN ou un numéro de TVA" in response.text


def test_list_clients_supports_type_filter_and_name_search(client: TestClient) -> None:
    client.post("/api/clients", json={"type": "Particulier", "name": "Alice"})
    client.post(
        "/api/clients",
        json={"type": "Entreprise", "name": "Alice Conseil", "vat_number": "FR00123456789"},
    )

    response = client.get("/api/clients", params={"type": "Entreprise", "search": "alice"})

    assert response.status_code == 200
    clients = response.json()
    assert len(clients) == 1
    assert clients[0]["name"] == "Alice Conseil"
