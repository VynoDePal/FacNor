from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "api@example.test") -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secret",
            "full_name": "API User",
            "siren": "123456789",
            "vat_number": "FRAB123456789",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_application_starts_initializes_schema_and_creates_invoice(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-test.db'}")

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        auth = _register(client)
        user_id = auth["user_id"]
        headers = {"Authorization": f"Bearer {auth['access_token']}"}

        client_response = client.post(
            "/clients",
            headers=headers,
            json={
                "name": "API Client",
                "address": "2 avenue de Lyon",
                "postal_code": "69001",
                "city": "Lyon",
                "siren": "987654321",
                "vat_number": "FRZZ987654321",
            },
        )
        assert client_response.status_code == 201
        assert client_response.json()["user_id"] == user_id
        client_id = client_response.json()["id"]

        invoice_response = client.post(
            "/invoices",
            headers=headers,
            json={
                "client_id": client_id,
                "lines": [
                    {
                        "description": "Développement",
                        "quantity": 1,
                        "unit_price_excluding_tax": 12000,
                        "vat_rate": 20,
                    }
                ],
            },
        )
        assert invoice_response.status_code == 201
        assert invoice_response.json()["user_id"] == user_id
        assert invoice_response.json()["invoice_number"] == "FAC-000001"
        assert invoice_response.json()["total_including_tax"] == 14400


def test_smoke_root_register_and_login_return_valid_tokens(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-auth.db'}")

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/").status_code == 200

        register_response = client.post(
            "/auth/register",
            json={"email": "auth@example.test", "password": "secret"},
        )
        assert register_response.status_code == 201
        register_body = register_response.json()
        assert register_body["token_type"] == "bearer"
        assert "password_hash" not in register_body["user"]

        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {register_body['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "auth@example.test"

        login_response = client.post(
            "/auth/login",
            json={"email": "auth@example.test", "password": "secret"},
        )
        assert login_response.status_code == 200
        login_body = login_response.json()
        assert login_body["token_type"] == "bearer"
        assert client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        ).status_code == 200


def test_protected_routes_require_valid_bearer_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-protected.db'}")

    from app.main import app

    with TestClient(app) as client:
        unauthorized = client.post(
            "/clients",
            json={"name": "Client", "address": "1 rue A", "postal_code": "75001", "city": "Paris"},
        )
        assert unauthorized.status_code == 401

        auth = _register(client, "owner@example.test")
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        forbidden = client.post(
            "/clients",
            headers=headers,
            json={
                "user_id": auth["user_id"] + 1,
                "name": "Client",
                "address": "1 rue A",
                "postal_code": "75001",
                "city": "Paris",
            },
        )
        assert forbidden.status_code == 403
