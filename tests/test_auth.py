import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


def test_register_creates_user_session_and_returns_valid_token(
    client: TestClient, database_path: Path
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "ADA@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Ada Lovelace",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"] == {
        "id": 1,
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
    }

    me_response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {payload['access_token']}"}
    )
    assert me_response.status_code == 200
    assert me_response.json() == payload["user"]

    with sqlite3.connect(database_path) as connection:
        stored_password = connection.execute(
            "SELECT hashed_password FROM users WHERE email = ?", ("ada@example.com",)
        ).fetchone()[0]
        session_count = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    assert stored_password != "correct-horse-battery-staple"
    assert stored_password.startswith("pbkdf2_sha256$")
    assert session_count == 1


def test_login_returns_a_session_token_for_existing_user(client: TestClient) -> None:
    register_response = client.post(
        "/auth/register",
        json={"email": "grace@example.com", "password": "strong-password"},
    )
    first_token = register_response.json()["access_token"]

    response = client.post(
        "/auth/login",
        json={"email": "grace@example.com", "password": "strong-password"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["access_token"] != first_token
    assert payload["user"]["email"] == "grace@example.com"


def test_login_rejects_invalid_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "marie@example.com", "password": "valid-password"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "marie@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {"email": "duplicate@example.com", "password": "valid-password"}
    assert client.post("/auth/register", json=payload).status_code == 201

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409


def test_me_rejects_missing_or_unknown_token(client: TestClient) -> None:
    missing_response = client.get("/auth/me")
    unknown_response = client.get(
        "/auth/me", headers={"Authorization": "Bearer unknown-token"}
    )

    assert missing_response.status_code == 401
    assert unknown_response.status_code == 401
