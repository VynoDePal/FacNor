from decimal import Decimal

from app.tax import TaxLineInput, calculate_invoice_totals
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
            {
                "description": "Prestation",
                "quantity": 2,
                "unit_price": 100,
                "tax_rate": 20,
            },
            {"description": "Frais", "quantity": 1, "unit_price": 50, "tax_rate": 10},
        ],
    }


def test_create_invoice_generates_sequential_number_and_returns_lines(client):
    user = register_user(client, "invoice-sequence@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"])

    first_response = client.post(
        "/invoices", headers=headers, json=invoice_payload(owned_client["id"])
    )
    second_response = client.post(
        "/invoices", headers=headers, json=invoice_payload(owned_client["id"])
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first_invoice = first_response.json()
    second_invoice = second_response.json()
    assert first_invoice["invoice_number"] == "FAC-2025-0001"
    assert second_invoice["invoice_number"] == "FAC-2025-0002"
    assert first_invoice["total_excluding_tax"] == 250
    assert first_invoice["total_tax"] == 45
    assert first_invoice["total_including_tax"] == 295
    assert [line["description"] for line in first_invoice["lines"]] == [
        "Prestation",
        "Frais",
    ]


def test_failed_invoice_creation_does_not_consume_sequence_number(client):
    user = register_user(client, "invoice-rollback@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"])

    invalid_response = client.post(
        "/invoices",
        headers=headers,
        json={
            **invoice_payload(owned_client["id"]),
            "lines": [{"description": "", "quantity": 1, "unit_price": 100}],
        },
    )
    valid_response = client.post(
        "/invoices", headers=headers, json=invoice_payload(owned_client["id"])
    )

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

    first_invoice_response = client.post(
        "/invoices", headers=first_headers, json=invoice_payload(first_client["id"])
    )
    second_invoice_response = client.post(
        "/invoices", headers=second_headers, json=invoice_payload(second_client["id"])
    )
    assert first_invoice_response.status_code == 201
    assert second_invoice_response.status_code == 201
    first_invoice = first_invoice_response.json()

    list_response = client.get("/invoices", headers=first_headers)
    get_response = client.get(f"/invoices/{first_invoice['id']}", headers=first_headers)
    forbidden_get_response = client.get(
        f"/invoices/{first_invoice['id']}", headers=second_headers
    )

    assert list_response.status_code == 200
    assert [invoice["id"] for invoice in list_response.json()] == [first_invoice["id"]]
    assert get_response.status_code == 200
    assert get_response.json()["lines"][0]["description"] == "Prestation"
    assert forbidden_get_response.status_code == 404


def test_get_invoice_never_exposes_another_users_invoice_or_lines(client):
    owner = register_user(client, "invoice-private-owner@example.com")
    attacker = register_user(client, "invoice-private-attacker@example.com")
    owner_headers = auth_headers(owner["access_token"])
    attacker_headers = auth_headers(attacker["access_token"])
    owned_client = create_owned_client(client, owner["access_token"], "Client privé")

    created_invoice = client.post(
        "/invoices", headers=owner_headers, json=invoice_payload(owned_client["id"])
    )
    assert created_invoice.status_code == 201
    invoice_id = created_invoice.json()["id"]

    attacker_response = client.get(f"/invoices/{invoice_id}", headers=attacker_headers)

    assert attacker_response.status_code == 404
    assert attacker_response.json() == {"detail": "Invoice not found"}


def test_manual_invoice_number_still_supported_and_checked(client):
    user = register_user(client, "invoice-manual@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"])
    payload = {
        **invoice_payload(owned_client["id"]),
        "invoice_number": "FAC-MANUAL-001",
    }

    first_response = client.post("/invoices", headers=headers, json=payload)
    duplicate_response = client.post("/invoices", headers=headers, json=payload)

    assert first_response.status_code == 201
    assert first_response.json()["invoice_number"] == "FAC-MANUAL-001"
    assert duplicate_response.status_code == 409


def test_tax_engine_totals_ttc_as_sum_of_taxed_lines():
    totals = calculate_invoice_totals(
        [
            TaxLineInput(
                quantity=Decimal(2), unit_price=Decimal("19.99"), tax_rate=Decimal(20)
            ),
            TaxLineInput(
                quantity=Decimal(3), unit_price=Decimal(10), tax_rate=Decimal("5.5")
            ),
        ],
    )

    assert totals.lines[0].total_excluding_tax == Decimal("39.98")
    assert totals.lines[0].total_tax == Decimal("7.996")
    assert totals.lines[0].total_including_tax == Decimal("47.976")
    assert totals.lines[1].total_excluding_tax == Decimal(30)
    assert totals.lines[1].total_tax == Decimal("1.650")
    assert totals.lines[1].total_including_tax == Decimal("31.650")
    assert totals.total_excluding_tax == Decimal("69.98")
    assert totals.total_tax == Decimal("9.646")
    assert totals.total_including_tax == Decimal("79.626")


def test_invoice_response_exposes_line_tax_and_ttc_totals(client):
    user = register_user(client, "invoice-tax-lines@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"])

    response = client.post(
        "/invoices",
        headers=headers,
        json={
            "client_id": owned_client["id"],
            "issue_date": "2025-01-15",
            "lines": [
                {
                    "description": "Abonnement",
                    "quantity": 2,
                    "unit_price": 19.99,
                    "tax_rate": 20,
                },
                {
                    "description": "Remise taxée",
                    "quantity": 3,
                    "unit_price": 10,
                    "tax_rate": 5.5,
                },
            ],
        },
    )

    assert response.status_code == 201
    invoice = response.json()
    assert invoice["total_excluding_tax"] == 69.98
    assert invoice["total_tax"] == 9.646
    assert invoice["total_including_tax"] == 79.626
    assert invoice["lines"][0]["line_total_excluding_tax"] == 39.98
    assert invoice["lines"][0]["line_total_tax"] == 7.996
    assert invoice["lines"][0]["line_total_including_tax"] == 47.976
    assert invoice["lines"][1]["line_total_excluding_tax"] == 30
    assert invoice["lines"][1]["line_total_tax"] == 1.65
    assert invoice["lines"][1]["line_total_including_tax"] == 31.65
    assert invoice["total_including_tax"] == sum(
        line["line_total_including_tax"] for line in invoice["lines"]
    )


def create_invoice_for_client(
    test_client, headers, owned_client, invoice_number, issue_date="2025-01-15"
):
    response = test_client.post(
        "/invoices",
        headers=headers,
        json={
            **invoice_payload(owned_client["id"], issue_date),
            "invoice_number": invoice_number,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_invoice_search_matches_client_name_or_invoice_number(client):
    user = register_user(client, "invoice-search@example.com")
    headers = auth_headers(user["access_token"])
    acme_client = create_owned_client(client, user["access_token"], "Acme Industrie")
    beta_client = create_owned_client(client, user["access_token"], "Beta Conseil")
    create_invoice_for_client(client, headers, acme_client, "FAC-2025-ACME")
    create_invoice_for_client(client, headers, beta_client, "FAC-2025-BETA")

    client_name_response = client.get("/invoices?search=acme", headers=headers)
    invoice_number_response = client.get("/invoices?search=BETA", headers=headers)

    assert client_name_response.status_code == 200
    assert [invoice["invoice_number"] for invoice in client_name_response.json()] == [
        "FAC-2025-ACME"
    ]
    assert client_name_response.json()[0]["client_name"] == "Acme Industrie"
    assert invoice_number_response.status_code == 200
    assert [invoice["client_name"] for invoice in invoice_number_response.json()] == [
        "Beta Conseil"
    ]


def test_invoice_filters_by_status_client_and_issue_date(client, connection):
    user = register_user(client, "invoice-filters@example.com")
    headers = auth_headers(user["access_token"])
    first_client = create_owned_client(client, user["access_token"], "Client Filtres A")
    second_client = create_owned_client(
        client, user["access_token"], "Client Filtres B"
    )
    draft_invoice = create_invoice_for_client(
        client, headers, first_client, "FAC-FILTER-DRAFT", "2025-01-10"
    )
    paid_invoice = create_invoice_for_client(
        client, headers, second_client, "FAC-FILTER-PAID", "2025-02-10"
    )
    connection.execute(
        "UPDATE invoices SET status = 'paid' WHERE id = ?", (paid_invoice["id"],)
    )
    connection.commit()

    status_response = client.get("/invoices?status_filter=paid", headers=headers)
    client_response = client.get(
        f"/invoices?client_id={first_client['id']}", headers=headers
    )
    date_response = client.get(
        "/invoices?issue_date_from=2025-02-01&issue_date_to=2025-02-28", headers=headers
    )

    assert status_response.status_code == 200
    assert [invoice["id"] for invoice in status_response.json()] == [paid_invoice["id"]]
    assert client_response.status_code == 200
    assert [invoice["id"] for invoice in client_response.json()] == [
        draft_invoice["id"]
    ]
    assert date_response.status_code == 200
    assert [invoice["invoice_number"] for invoice in date_response.json()] == [
        "FAC-FILTER-PAID"
    ]


def test_invoice_search_stays_scoped_to_owner_and_fast(client):
    first_user = register_user(client, "invoice-fast-owner@example.com")
    second_user = register_user(client, "invoice-fast-other@example.com")
    first_headers = auth_headers(first_user["access_token"])
    second_headers = auth_headers(second_user["access_token"])
    first_client = create_owned_client(
        client, first_user["access_token"], "Chrono Client"
    )
    second_client = create_owned_client(
        client, second_user["access_token"], "Chrono Client"
    )

    for index in range(80):
        create_invoice_for_client(
            client, first_headers, first_client, f"FAC-FAST-{index:04d}"
        )
    create_invoice_for_client(client, second_headers, second_client, "FAC-FAST-OTHER")

    import time

    start = time.perf_counter()
    response = client.get("/invoices?search=FAC-FAST-0079", headers=first_headers)
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 2
    assert [invoice["invoice_number"] for invoice in response.json()] == [
        "FAC-FAST-0079"
    ]


def test_invoice_filters_reject_invalid_values(client):
    user = register_user(client, "invoice-invalid-filter@example.com")
    headers = auth_headers(user["access_token"])

    invalid_status_response = client.get(
        "/invoices?status_filter=archived", headers=headers
    )
    invalid_range_response = client.get(
        "/invoices?issue_date_from=2025-03-01&issue_date_to=2025-02-01", headers=headers
    )

    assert invalid_status_response.status_code == 422
    assert invalid_range_response.status_code == 422
