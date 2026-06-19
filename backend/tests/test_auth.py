from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.main import app


PUBLIC_USER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "secure-password",
    "company_name": "FacNor SAS",
    "siren": "123456789",
    "vat_number": "FR12345678901",
    "address": "1 rue de Paris, 75000 Paris",
}


def test_register_login_and_read_current_user() -> None:
    with auth_client() as client:
        register_response = client.post("/api/auth/register", json=PUBLIC_USER_PAYLOAD)

        assert register_response.status_code == 201
        register_body = register_response.json()
        assert register_body["token_type"] == "bearer"
        assert register_body["access_token"]
        assert register_body["user"]["email"] == "owner@example.com"
        assert "password" not in register_body["user"]

        login_response = client.post(
            "/api/auth/login",
            json={"email": PUBLIC_USER_PAYLOAD["email"], "password": PUBLIC_USER_PAYLOAD["password"]},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["company_name"] == "FacNor SAS"


def test_protected_endpoint_rejects_unauthenticated_user() -> None:
    with auth_client() as client:
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_invalid_credentials() -> None:
    with auth_client() as client:
        client.post("/api/auth/register", json=PUBLIC_USER_PAYLOAD)

        response = client.post("/api/auth/login", json={"email": PUBLIC_USER_PAYLOAD["email"], "password": "wrong-password"})

        assert response.status_code == 401


class auth_client:
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
