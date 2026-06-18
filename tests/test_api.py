from app.main import decode_access_token


def register_user(client, email="ada@example.com"):
    response = client.post(
        "/users",
        json={
            "email": email,
            "full_name": "Ada Lovelace",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_user_returns_valid_jwt(client):
    user = register_user(client)

    token = user["access_token"]
    payload = decode_access_token(token)

    assert token.count(".") == 2
    assert user["token_type"] == "bearer"
    assert payload["sub"] == str(user["id"])
    assert payload["email"] == "ada@example.com"
    assert payload["exp"] > payload["iat"]


def test_login_returns_valid_jwt_for_following_requests(client):
    registered_user = register_user(client)

    login_response = client.post(
        "/auth/login",
        json={"email": "ada@example.com", "password": "correct horse battery staple"},
    )
    assert login_response.status_code == 200
    login_token = login_response.json()["access_token"]
    login_payload = decode_access_token(login_token)
    assert login_payload["sub"] == str(registered_user["id"])
    assert login_payload["email"] == "ada@example.com"

    client_response = client.post(
        "/clients",
        headers=auth_headers(login_token),
        json={"name": "Société Exemple", "address": "10 rue de la Paix, 75002 Paris"},
    )
    assert client_response.status_code == 201


def test_login_rejects_invalid_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={"email": "ada@example.com", "password": "mauvais mot de passe"},
    )

    assert response.status_code == 401


def test_create_invoice_flow(client):
    user = register_user(client)
    user_id = user["id"]
    headers = auth_headers(user["access_token"])

    client_response = client.post(
        "/clients",
        headers=headers,
        json={
            "user_id": 999,
            "name": "Société Exemple",
            "email": "billing@example.com",
            "address": "10 rue de la Paix, 75002 Paris",
            "vat_number": "FR12345678901",
        },
    )
    assert client_response.status_code == 201
    assert client_response.json()["user_id"] == user_id
    client_id = client_response.json()["id"]

    invoice_response = client.post(
        "/invoices",
        headers=headers,
        json={
            "user_id": 999,
            "client_id": client_id,
            "invoice_number": "FAC-2025-0001",
            "issue_date": "2025-01-15",
            "lines": [
                {
                    "description": "Prestation",
                    "quantity": 2,
                    "unit_price": 100,
                    "tax_rate": 20,
                },
            ],
        },
    )

    assert invoice_response.status_code == 201
    assert invoice_response.json()["total_excluding_tax"] == 200
    assert invoice_response.json()["total_tax"] == 40
    assert invoice_response.json()["total_including_tax"] == 240


def test_protected_endpoints_require_authentication(client):
    assert (
        client.post(
            "/clients",
            json={
                "name": "Société Exemple",
                "address": "10 rue de la Paix, 75002 Paris",
            },
        ).status_code
        == 401
    )

    assert (
        client.post(
            "/invoices",
            json={
                "client_id": 1,
                "invoice_number": "FAC-2025-0002",
                "issue_date": "2025-01-15",
                "lines": [
                    {"description": "Prestation", "quantity": 1, "unit_price": 100}
                ],
            },
        ).status_code
        == 401
    )


def test_invoice_cannot_use_another_users_client(client):
    first_user = register_user(client, "first@example.com")
    second_user = register_user(client, "second@example.com")

    first_client_response = client.post(
        "/clients",
        headers=auth_headers(first_user["access_token"]),
        json={"name": "Client premier", "address": "1 rue A"},
    )
    assert first_client_response.status_code == 201

    invoice_response = client.post(
        "/invoices",
        headers=auth_headers(second_user["access_token"]),
        json={
            "client_id": first_client_response.json()["id"],
            "invoice_number": "FAC-2025-0003",
            "issue_date": "2025-01-15",
            "lines": [{"description": "Prestation", "quantity": 1, "unit_price": 100}],
        },
    )

    assert invoice_response.status_code == 404


def test_client_payload_cannot_assign_another_owner(client, connection):
    first_user = register_user(client, "owner@example.com")
    second_user = register_user(client, "attacker@example.com")

    response = client.post(
        "/clients",
        headers=auth_headers(first_user["access_token"]),
        json={"user_id": second_user["id"], "name": "Client", "address": "1 rue A"},
    )

    assert response.status_code == 201
    client_id = response.json()["id"]
    stored_client = connection.execute(
        "SELECT user_id FROM clients WHERE id = ?", (client_id,)
    ).fetchone()
    assert response.json()["user_id"] == first_user["id"]
    assert stored_client["user_id"] == first_user["id"]


def test_invoice_payload_cannot_assign_another_owner(client, connection):
    first_user = register_user(client, "invoice-owner@example.com")
    second_user = register_user(client, "invoice-attacker@example.com")
    client_response = client.post(
        "/clients",
        headers=auth_headers(first_user["access_token"]),
        json={"name": "Client", "address": "1 rue A"},
    )
    assert client_response.status_code == 201

    response = client.post(
        "/invoices",
        headers=auth_headers(first_user["access_token"]),
        json={
            "user_id": second_user["id"],
            "client_id": client_response.json()["id"],
            "invoice_number": "FAC-2025-OWNER",
            "issue_date": "2025-01-15",
            "lines": [{"description": "Prestation", "quantity": 1, "unit_price": 100}],
        },
    )

    assert response.status_code == 201
    invoice_id = response.json()["id"]
    stored_invoice = connection.execute(
        "SELECT user_id FROM invoices WHERE id = ?", (invoice_id,)
    ).fetchone()
    assert stored_invoice["user_id"] == first_user["id"]


def test_invoice_number_uniqueness_is_scoped_to_owner(client):
    first_user = register_user(client, "scoped-first@example.com")
    second_user = register_user(client, "scoped-second@example.com")

    first_client = client.post(
        "/clients",
        headers=auth_headers(first_user["access_token"]),
        json={"name": "Client A", "address": "1 rue A"},
    )
    second_client = client.post(
        "/clients",
        headers=auth_headers(second_user["access_token"]),
        json={"name": "Client B", "address": "2 rue B"},
    )
    assert first_client.status_code == 201
    assert second_client.status_code == 201

    payload = {
        "invoice_number": "FAC-2025-SHARED",
        "issue_date": "2025-01-15",
        "lines": [{"description": "Prestation", "quantity": 1, "unit_price": 100}],
    }
    first_invoice = client.post(
        "/invoices",
        headers=auth_headers(first_user["access_token"]),
        json={**payload, "client_id": first_client.json()["id"]},
    )
    second_invoice = client.post(
        "/invoices",
        headers=auth_headers(second_user["access_token"]),
        json={**payload, "client_id": second_client.json()["id"]},
    )
    duplicate_invoice = client.post(
        "/invoices",
        headers=auth_headers(first_user["access_token"]),
        json={**payload, "client_id": first_client.json()["id"]},
    )

    assert first_invoice.status_code == 201
    assert second_invoice.status_code == 201
    assert duplicate_invoice.status_code == 409
