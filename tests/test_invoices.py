import time

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


def test_invoice_crud_with_items_and_totals(client: TestClient) -> None:
    headers = _auth_headers(client)
    client_id = _create_individual_client(client, headers)
    payload = {
        "client_id": client_id,
        "issue_date": "2024-01-15",
        "due_date": "2024-02-15",
        "items": [
            {
                "description": "Prestation",
                "quantity": "2",
                "unit_price_excluding_tax": "100.00",
                "vat_rate": "20",
            },
            {
                "description": "Remise taxable",
                "quantity": "3",
                "unit_price_excluding_tax": "10.50",
                "vat_rate": "5.5",
            },
        ],
    }

    created = client.post("/invoices", headers=headers, json=payload)

    assert created.status_code == 201
    created_data = created.json()
    assert created_data["total_excluding_tax"] == "231.5"
    assert created_data["total_vat"] == "41.73"
    assert created_data["total_including_tax"] == "273.23"
    assert len(created_data["items"]) == 2
    assert created_data["items"][0]["line_total_excluding_tax"] == "200.0"
    assert created_data["items"][0]["line_total_vat"] == "40.0"
    assert created_data["items"][0]["line_total_including_tax"] == "240.0"

    invoice_id = created_data["id"]
    fetched = client.get(f"/invoices/{invoice_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["invoice_number"] == "FAC-000001"
    assert fetched.json()["items"][1]["line_total_vat"] == "1.73"

    updated = client.put(
        f"/invoices/{invoice_id}",
        headers=headers,
        json={
            "status": "issued",
            "items": [
                {
                    "description": "Forfait",
                    "quantity": "1",
                    "unit_price_excluding_tax": "99.99",
                    "vat_rate": "20",
                }
            ],
        },
    )
    assert updated.status_code == 200
    updated_data = updated.json()
    assert updated_data["status"] == "issued"
    assert updated_data["total_excluding_tax"] == "99.99"
    assert updated_data["total_vat"] == "20.0"
    assert updated_data["total_including_tax"] == "119.99"
    assert len(updated_data["items"]) == 1

    deleted = client.delete(f"/invoices/{invoice_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/invoices/{invoice_id}", headers=headers).status_code == 404


def test_invoice_access_is_limited_to_owner(client: TestClient) -> None:
    first_headers = _auth_headers(client, "owner-a@example.com")
    second_headers = _auth_headers(client, "owner-b@example.com")
    first_client_id = _create_individual_client(client, first_headers, "Owner A")
    invoice = client.post("/invoices", headers=first_headers, json={"client_id": first_client_id})
    assert invoice.status_code == 201

    invoice_id = invoice.json()["id"]
    assert client.get(f"/invoices/{invoice_id}", headers=second_headers).status_code == 404
    assert client.put(f"/invoices/{invoice_id}", headers=second_headers, json={"status": "paid"}).status_code == 404
    assert client.delete(f"/invoices/{invoice_id}", headers=second_headers).status_code == 404


def test_list_invoices_searches_by_client_name_or_invoice_number(client: TestClient) -> None:
    headers = _auth_headers(client)
    alpha_client_id = _create_individual_client(client, headers, "Alpha Conseil")
    beta_client_id = _create_individual_client(client, headers, "Beta Services")

    first = client.post("/invoices", headers=headers, json={"client_id": alpha_client_id, "issue_date": "2024-01-10"})
    second = client.post("/invoices", headers=headers, json={"client_id": beta_client_id, "issue_date": "2024-01-11"})
    assert first.status_code == 201
    assert second.status_code == 201

    by_client = client.get("/invoices", headers=headers, params={"q": "alpha"})
    assert by_client.status_code == 200
    assert [invoice["invoice_number"] for invoice in by_client.json()] == ["FAC-000001"]

    by_number = client.get("/invoices", headers=headers, params={"q": "000002"})
    assert by_number.status_code == 200
    assert [invoice["client_id"] for invoice in by_number.json()] == [beta_client_id]


def test_list_invoices_filters_by_status_client_and_issue_date(client: TestClient) -> None:
    headers = _auth_headers(client)
    alpha_client_id = _create_individual_client(client, headers, "Alpha Conseil")
    beta_client_id = _create_individual_client(client, headers, "Beta Services")

    draft_alpha = client.post(
        "/invoices",
        headers=headers,
        json={"client_id": alpha_client_id, "status": "draft", "issue_date": "2024-01-10"},
    )
    issued_alpha = client.post(
        "/invoices",
        headers=headers,
        json={"client_id": alpha_client_id, "status": "issued", "issue_date": "2024-02-15"},
    )
    issued_beta = client.post(
        "/invoices",
        headers=headers,
        json={"client_id": beta_client_id, "status": "issued", "issue_date": "2024-03-20"},
    )
    assert draft_alpha.status_code == 201
    assert issued_alpha.status_code == 201
    assert issued_beta.status_code == 201

    filtered = client.get(
        "/invoices",
        headers=headers,
        params={
            "status": "issued",
            "client_id": alpha_client_id,
            "issue_date_from": "2024-02-01",
            "issue_date_to": "2024-02-29",
        },
    )

    assert filtered.status_code == 200
    assert [invoice["invoice_number"] for invoice in filtered.json()] == ["FAC-000002"]


def test_invoice_search_is_limited_to_current_user(client: TestClient) -> None:
    first_headers = _auth_headers(client, "search-owner-a@example.com")
    second_headers = _auth_headers(client, "search-owner-b@example.com")
    first_client_id = _create_individual_client(client, first_headers, "Secret Client")
    second_client_id = _create_individual_client(client, second_headers, "Visible Client")
    assert client.post("/invoices", headers=first_headers, json={"client_id": first_client_id}).status_code == 201
    assert client.post("/invoices", headers=second_headers, json={"client_id": second_client_id}).status_code == 201

    response = client.get("/invoices", headers=second_headers, params={"q": "secret"})

    assert response.status_code == 200
    assert response.json() == []


def test_invoice_search_responds_under_two_seconds(client: TestClient) -> None:
    headers = _auth_headers(client)
    target_client_id = _create_individual_client(client, headers, "Performance Target")
    other_client_id = _create_individual_client(client, headers, "Performance Other")
    for index in range(40):
        client_id = target_client_id if index == 17 else other_client_id
        response = client.post(
            "/invoices",
            headers=headers,
            json={"client_id": client_id, "issue_date": "2024-04-01"},
        )
        assert response.status_code == 201

    started_at = time.perf_counter()
    response = client.get("/invoices", headers=headers, params={"q": "target"})
    elapsed = time.perf_counter() - started_at

    assert response.status_code == 200
    assert elapsed < 2
    assert [invoice["client_id"] for invoice in response.json()] == [target_client_id]


