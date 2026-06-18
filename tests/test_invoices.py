from tests.test_api import auth_headers, register_user


def create_owned_client(client, token, name="Client Facture"):
    response = client.post(
        "/clients",
        headers=auth_headers(token),
        json={"name": name, "address": "1 rue de Paris"},
    )
    assert response.status_code == 201
    return response.json()


def invoice_payload(client_id, issue_date="2025-01-15"):
    return {
        "client_id": client_id,
        "issue_date": issue_date,
        "lines": [
            {"description": "Prestation", "quantity": 2, "unit_price": 100, "tax_rate": 20},
            {"description": "Frais", "quantity": 1, "unit_price": 50, "tax_rate": 10},
        ],
    }


def test_create_invoice_generates_sequential_number_and_returns_lines(client):
    user = register_user(client, "invoice-sequence@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"])

    first_response = client.post("/invoices", headers=headers, json=invoice_payload(owned_client["id"]))
    second_response = client.post("/invoices", headers=headers, json=invoice_payload(owned_client["id"]))

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first_invoice = first_response.json()
    second_invoice = second_response.json()
    assert first_invoice["invoice_number"] == "FAC-2025-0001"
    assert second_invoice["invoice_number"] == "FAC-2025-0002"
    assert first_invoice["total_excluding_tax"] == 250
    assert first_invoice["total_tax"] == 45
    assert first_invoice["total_including_tax"] == 295
    assert [line["description"] for line in first_invoice["lines"]] == ["Prestation", "Frais"]


def test_failed_invoice_creation_does_not_consume_sequence_number(client):
    user = register_user(client, "invoice-rollback@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"])

    invalid_response = client.post(
        "/invoices",
        headers=headers,
        json={**invoice_payload(owned_client["id"]), "lines": [{"description": "", "quantity": 1, "unit_price": 100}]},
    )
    valid_response = client.post("/invoices", headers=headers, json=invoice_payload(owned_client["id"]))

    assert invalid_response.status_code == 422
    assert valid_response.status_code == 201
    assert valid_response.json()["invoice_number"] == "FAC-2025-0001"


def test_list_and_get_invoices_are_scoped_to_owner(client):
    first_user = register_user(client, "invoice-owner-a@example.com")
    second_user = register_user(client, "invoice-owner-b@example.com")
    first_headers = auth_headers(first_user["access_token"])
    second_headers = auth_headers(second_user["access_token"])
    first_client = create_owned_client(client, first_user["access_token"], "Client A")
    second_client = create_owned_client(client, second_user["access_token"], "Client B")

    first_invoice_response = client.post("/invoices", headers=first_headers, json=invoice_payload(first_client["id"]))
    second_invoice_response = client.post("/invoices", headers=second_headers, json=invoice_payload(second_client["id"]))
    assert first_invoice_response.status_code == 201
    assert second_invoice_response.status_code == 201
    first_invoice = first_invoice_response.json()

    list_response = client.get("/invoices", headers=first_headers)
    get_response = client.get(f"/invoices/{first_invoice['id']}", headers=first_headers)
    forbidden_get_response = client.get(f"/invoices/{first_invoice['id']}", headers=second_headers)

    assert list_response.status_code == 200
    assert [invoice["id"] for invoice in list_response.json()] == [first_invoice["id"]]
    assert get_response.status_code == 200
    assert get_response.json()["lines"][0]["description"] == "Prestation"
    assert forbidden_get_response.status_code == 404


def test_manual_invoice_number_still_supported_and_checked(client):
    user = register_user(client, "invoice-manual@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"])
    payload = {**invoice_payload(owned_client["id"]), "invoice_number": "FAC-MANUAL-001"}

    first_response = client.post("/invoices", headers=headers, json=payload)
    duplicate_response = client.post("/invoices", headers=headers, json=payload)

    assert first_response.status_code == 201
    assert first_response.json()["invoice_number"] == "FAC-MANUAL-001"
    assert duplicate_response.status_code == 409
