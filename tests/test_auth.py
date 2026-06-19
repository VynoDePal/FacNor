from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base, get_db
from app.main import create_app
import app.models  # noqa: F401


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


def test_register_login_and_read_current_user(client: TestClient) -> None:
    register_response = client.post(
        "/auth/register",
        json={"email": "User@example.com", "password": "motdepasse-solide"},
    )

    assert register_response.status_code == 201
    assert register_response.json()["email"] == "user@example.com"
    assert "hashed_password" not in register_response.json()

    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "motdepasse-solide"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert login_response.json()["token_type"] == "bearer"

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {"email": "duplicate@example.com", "password": "motdepasse-solide"}
    assert client.post("/auth/register", json=payload).status_code == 201

    duplicate_response = client.post("/auth/register", json=payload)

    assert duplicate_response.status_code == 409


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    client.post("/auth/register", json={"email": "user@example.com", "password": "motdepasse-solide"})

    response = client.post("/auth/login", json={"email": "user@example.com", "password": "erreur"})

    assert response.status_code == 401


def test_protected_route_rejects_missing_or_invalid_token(client: TestClient) -> None:
    missing_response = client.get("/auth/me")
    invalid_response = client.get("/auth/me", headers={"Authorization": "Bearer invalide"})

    assert missing_response.status_code == 401
    assert invalid_response.status_code == 401
