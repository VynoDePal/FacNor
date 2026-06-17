def register_user(client, email="ada@example.com"):
    response = client.post(
        "/users",
        json={"email": email, "full_name": "Ada Lovelace", "password": "correct horse battery staple"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
                {"description": "Prestation", "quantity": 2, "unit_price": 100, "tax_rate": 20}
            ],
        },
    )

    assert invoice_response.status_code == 201
    assert invoice_response.json()["total_excluding_tax"] == 200
    assert invoice_response.json()["total_tax"] == 40
    assert invoice_response.json()["total_including_tax"] == 240


def test_protected_endpoints_require_authentication(client):
    assert client.post(
        "/clients",
        json={"name": "Société Exemple", "address": "10 rue de la Paix, 75002 Paris"},
    ).status_code == 401

    assert client.post(
        "/invoices",
        json={
            "client_id": 1,
            "invoice_number": "FAC-2025-0002",
            "issue_date": "2025-01-15",
            "lines": [{"description": "Prestation", "quantity": 1, "unit_price": 100}],
        },
    ).status_code == 401


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
