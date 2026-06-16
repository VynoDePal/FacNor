from __future__ import annotations

from fastapi.testclient import TestClient


def test_application_starts_initializes_schema_and_creates_invoice(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-test.db'}")

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        user_response = client.post(
            "/users",
            json={
                "email": "api@example.test",
                "full_name": "API User",
                "password_hash": "hash",
                "siren": "123456789",
                "vat_number": "FRAB123456789",
            },
        )
        assert user_response.status_code == 201
        user_id = user_response.json()["id"]

        client_response = client.post(
            "/clients",
            json={
                "user_id": user_id,
                "name": "API Client",
                "address": "2 avenue de Lyon",
                "postal_code": "69001",
                "city": "Lyon",
                "siren": "987654321",
                "vat_number": "FRZZ987654321",
            },
        )
        assert client_response.status_code == 201
        client_id = client_response.json()["id"]

        invoice_response = client.post(
            "/invoices",
            json={
                "user_id": user_id,
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
        assert invoice_response.json()["invoice_number"] == "FAC-000001"
        assert invoice_response.json()["total_including_tax"] == 14400


def test_smoke_root_register_and_login(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-auth.db'}")

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/").status_code == 200

        register_response = client.post(
            "/auth/register",
            json={"email": "auth@example.test", "password": "secret"},
        )
        assert register_response.status_code == 201
        assert "password_hash" not in register_response.json()

        login_response = client.post(
            "/auth/login",
            json={"email": "auth@example.test", "password": "secret"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["token_type"] == "bearer"

