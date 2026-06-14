from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str = "owner@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "correct-password"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_individual_client(client: TestClient, headers: dict[str, str], name: str = "Client") -> int:
    response = client.post(
        "/clients",
        headers=headers,
        json={"name": name, "client_type": "individual"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_invoice_numbers_are_sequential_unique_and_continuous(client: TestClient) -> None:
    headers = _auth_headers(client)
    client_id = _create_individual_client(client, headers)

    first = client.post("/invoices", headers=headers, json={"client_id": client_id})
    second = client.post("/invoices", headers=headers, json={"client_id": client_id})
    third = client.post("/invoices", headers=headers, json={"client_id": client_id})

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 201
    assert [
        first.json()["invoice_number"],
        second.json()["invoice_number"],
        third.json()["invoice_number"],
    ] == ["FAC-000001", "FAC-000002", "FAC-000003"]

    list_response = client.get("/invoices", headers=headers)
    assert list_response.status_code == 200
    assert [invoice["invoice_number"] for invoice in list_response.json()] == [
        "FAC-000001",
        "FAC-000002",
        "FAC-000003",
    ]


def test_failed_invoice_creation_does_not_consume_number(client: TestClient) -> None:
    headers = _auth_headers(client)
    valid_client_id = _create_individual_client(client, headers)

    missing_client_response = client.post(
        "/invoices",
        headers=headers,
        json={"client_id": valid_client_id + 999},
    )
    assert missing_client_response.status_code == 404

    created = client.post("/invoices", headers=headers, json={"client_id": valid_client_id})
    assert created.status_code == 201
    assert created.json()["invoice_number"] == "FAC-000001"


def test_invoice_numbers_are_globally_unique_across_users(client: TestClient) -> None:
    first_headers = _auth_headers(client, "first@example.com")
    second_headers = _auth_headers(client, "second@example.com")
    first_client_id = _create_individual_client(client, first_headers, "Premier")
    second_client_id = _create_individual_client(client, second_headers, "Second")

    first_invoice = client.post("/invoices", headers=first_headers, json={"client_id": first_client_id})
    second_invoice = client.post("/invoices", headers=second_headers, json={"client_id": second_client_id})

    assert first_invoice.status_code == 201
    assert second_invoice.status_code == 201
    assert first_invoice.json()["invoice_number"] == "FAC-000001"
    assert second_invoice.json()["invoice_number"] == "FAC-000002"
    assert client.get("/invoices", headers=first_headers).json()[0]["invoice_number"] == "FAC-000001"
    assert client.get("/invoices", headers=second_headers).json()[0]["invoice_number"] == "FAC-000002"


def test_invoice_creation_requires_authentication(client: TestClient) -> None:
    response = client.post("/invoices", json={"client_id": 1})
    assert response.status_code == 401
