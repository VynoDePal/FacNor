from fastapi.testclient import TestClient

from app.auth import decode_access_token
from app.database import connect
from main import app


REGISTRATION_PAYLOAD = {
    "email": "Admin@Facnor.test",
    "password": "MotDePasseSecurise123",
    "full_name": "Marie Martin",
    "company_name": "FacNor Demo",
    "company_siren": "123456789",
    "company_vat_number": "FR00123456789",
}


def test_user_can_register_and_receive_valid_jwt(database_path):
    with TestClient(app) as client:
        response = client.post("/auth/register", json=REGISTRATION_PAYLOAD)

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] > 0
    assert payload["user"]["email"] == "admin@facnor.test"
    assert payload["user"]["company_name"] == "FacNor Demo"

    token_payload = decode_access_token(payload["access_token"])
    assert token_payload["email"] == "admin@facnor.test"
    assert int(token_payload["sub"]) == payload["user"]["id"]

    with connect(database_path) as connection:
        row = connection.execute("SELECT password_hash FROM users WHERE email = ?", ("admin@facnor.test",)).fetchone()
    assert row is not None
    assert row["password_hash"].startswith("pbkdf2_sha256$")
    assert "MotDePasseSecurise123" not in row["password_hash"]


def test_user_can_login_and_call_authenticated_endpoint(database_path):
    with TestClient(app) as client:
        client.post("/auth/register", json=REGISTRATION_PAYLOAD)
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@facnor.test", "password": "MotDePasseSecurise123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@facnor.test"
    assert me_response.json()["full_name"] == "Marie Martin"


def test_login_rejects_invalid_password(database_path):
    with TestClient(app) as client:
        client.post("/auth/register", json=REGISTRATION_PAYLOAD)
        response = client.post(
            "/auth/login",
            json={"email": "admin@facnor.test", "password": "mauvais-secret"},
        )

    assert response.status_code == 401


def test_registration_rejects_duplicate_email(database_path):
    with TestClient(app) as client:
        first_response = client.post("/auth/register", json=REGISTRATION_PAYLOAD)
        duplicate_response = client.post("/auth/register", json=REGISTRATION_PAYLOAD)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_authenticated_endpoint_requires_bearer_token(database_path):
    with TestClient(app) as client:
        response = client.get("/auth/me")

    assert response.status_code == 401
