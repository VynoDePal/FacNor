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



def test_frontend_origin_can_call_auth_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-cors.db'}")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")

    from app.main import app

    with TestClient(app) as client:
        response = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


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


def test_authenticated_user_can_crud_only_own_clients(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-clients.db'}")

    from app.main import app

    with TestClient(app) as client:
        owner_auth = _register(client, "owner-crud@example.test")
        other_auth = _register(client, "other-crud@example.test")
        owner_headers = {"Authorization": f"Bearer {owner_auth['access_token']}"}
        other_headers = {"Authorization": f"Bearer {other_auth['access_token']}"}

        create_response = client.post(
            "/clients",
            headers=owner_headers,
            json={
                "name": "Client Initial",
                "email": "initial@example.test",
                "address": "10 rue des Tests",
                "postal_code": "31000",
                "city": "Toulouse",
                "siren": "111222333",
                "vat_number": "FRAB111222333",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["user_id"] == owner_auth["user_id"]
        client_id = created["id"]

        assert client.get("/clients", headers=owner_headers).json() == [created]
        assert client.get("/clients", headers=other_headers).json() == []

        detail_response = client.get(f"/clients/{client_id}", headers=owner_headers)
        assert detail_response.status_code == 200
        assert detail_response.json()["name"] == "Client Initial"
        assert client.get(f"/clients/{client_id}", headers=other_headers).status_code == 404

        update_response = client.put(
            f"/clients/{client_id}",
            headers=owner_headers,
            json={"name": "Client Modifié", "city": "Bordeaux", "email": None},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "Client Modifié"
        assert updated["city"] == "Bordeaux"
        assert updated["email"] is None
        assert updated["address"] == "10 rue des Tests"

        forbidden_update = client.put(
            f"/clients/{client_id}",
            headers=other_headers,
            json={"name": "Tentative interdite"},
        )
        assert forbidden_update.status_code == 404
        assert client.delete(f"/clients/{client_id}", headers=other_headers).status_code == 404

        delete_response = client.delete(f"/clients/{client_id}", headers=owner_headers)
        assert delete_response.status_code == 204
        assert delete_response.content == b""
        assert client.get(f"/clients/{client_id}", headers=owner_headers).status_code == 404
        assert client.get("/clients", headers=owner_headers).json() == []

