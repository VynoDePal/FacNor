from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.database import connect
from main import app


def create_user(database_path, email="invoice-crud@example.com"):
    with connect(database_path) as connection:
        return connection.execute(
            "INSERT INTO users (email, password_hash, full_name, company_name) VALUES (?, ?, ?, ?)",
            (email, "hash", "Invoice Owner", "Owner SAS"),
        ).lastrowid


def create_client(database_path, user_id, name="Client Facture"):
    with connect(database_path) as connection:
        return connection.execute(
            """
            INSERT INTO clients (user_id, client_type, name, address_line1, postal_code, city)
            VALUES (?, 'B2C', ?, '1 rue Test', '44000', 'Nantes')
            """,
            (user_id, name),
        ).lastrowid


def auth_headers(user_id, email="invoice-crud@example.com"):
    return {"Authorization": f"Bearer {create_access_token(user_id, email)}"}


INVOICE_PAYLOAD = {
    "issue_date": "2024-04-01",
    "due_date": "2024-04-30",
    "lines": [
        {
            "description": "Prestation initiale",
            "quantity": "2",
            "unit_price_excluding_tax": "100",
            "vat_rate": "20",
        }
    ],
}


def test_authenticated_user_can_create_list_read_update_and_delete_invoices(database_path):
    user_id = create_user(database_path)
    client_id = create_client(database_path, user_id)

    with TestClient(app) as client:
        create_response = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": client_id},
            headers=auth_headers(user_id),
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["invoice_number"] == "F-001"
        assert created["total_including_tax"] == "240.00"
        assert created["lines"][0]["description"] == "Prestation initiale"

        list_response = client.get("/invoices", headers=auth_headers(user_id))
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()] == [created["id"]]

        read_response = client.get(f"/invoices/{created['id']}", headers=auth_headers(user_id))
        assert read_response.status_code == 200
        assert read_response.json()["invoice_number"] == "F-001"

        update_response = client.patch(
            f"/invoices/{created['id']}",
            json={
                "status": "issued",
                "due_date": None,
                "lines": [
                    {
                        "description": "Prestation modifiée",
                        "quantity": "3",
                        "unit_price_excluding_tax": "50",
                        "vat_rate": "10",
                    }
                ],
            },
            headers=auth_headers(user_id),
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["invoice_number"] == "F-001"
        assert updated["status"] == "issued"
        assert updated["due_date"] is None
        assert updated["total_excluding_tax"] == "150.00"
        assert updated["total_tax"] == "15.00"
        assert updated["total_including_tax"] == "165.00"
        assert updated["lines"][0]["line_order"] == 1
        assert updated["lines"][0]["description"] == "Prestation modifiée"

        delete_response = client.delete(f"/invoices/{created['id']}", headers=auth_headers(user_id))
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        missing_response = client.get(f"/invoices/{created['id']}", headers=auth_headers(user_id))
        assert missing_response.status_code == 404


def test_invoice_crud_is_scoped_to_authenticated_user(database_path):
    first_user_id = create_user(database_path, "first-invoice-owner@example.com")
    second_user_id = create_user(database_path, "second-invoice-owner@example.com")
    first_client_id = create_client(database_path, first_user_id)

    with TestClient(app) as client:
        create_response = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": first_client_id},
            headers=auth_headers(first_user_id, "first-invoice-owner@example.com"),
        )
        assert create_response.status_code == 201
        invoice_id = create_response.json()["id"]

        second_headers = auth_headers(second_user_id, "second-invoice-owner@example.com")
        assert client.get(f"/invoices/{invoice_id}", headers=second_headers).status_code == 404
        assert client.patch(f"/invoices/{invoice_id}", json={"status": "paid"}, headers=second_headers).status_code == 404
        assert client.delete(f"/invoices/{invoice_id}", headers=second_headers).status_code == 404
        assert client.get("/invoices", headers=second_headers).json() == []


def test_invoice_update_validates_client_ownership_and_business_rules(database_path):
    first_user_id = create_user(database_path, "first-validation@example.com")
    second_user_id = create_user(database_path, "second-validation@example.com")
    first_client_id = create_client(database_path, first_user_id)
    second_client_id = create_client(database_path, second_user_id)

    with TestClient(app) as client:
        create_response = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": first_client_id},
            headers=auth_headers(first_user_id, "first-validation@example.com"),
        )
        invoice_id = create_response.json()["id"]
        headers = auth_headers(first_user_id, "first-validation@example.com")

        wrong_client = client.patch(f"/invoices/{invoice_id}", json={"client_id": second_client_id}, headers=headers)
        assert wrong_client.status_code == 404

        invalid_status = client.patch(f"/invoices/{invoice_id}", json={"status": "sent"}, headers=headers)
        assert invalid_status.status_code == 422

        invalid_line = client.patch(
            f"/invoices/{invoice_id}",
            json={"lines": [{"description": "", "quantity": "0", "unit_price_excluding_tax": "10", "vat_rate": "20"}]},
            headers=headers,
        )
        assert invalid_line.status_code == 422


def test_invoice_list_returns_invoices_with_lines_ordered_by_recent_issue_date(database_path):
    user_id = create_user(database_path)
    client_id = create_client(database_path, user_id)

    with TestClient(app) as client:
        first = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": client_id, "issue_date": "2024-01-01"},
            headers=auth_headers(user_id),
        )
        second = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": client_id, "issue_date": "2024-02-01"},
            headers=auth_headers(user_id),
        )
        response = client.get("/invoices", headers=auth_headers(user_id))

    assert first.status_code == 201
    assert second.status_code == 201
    payload = response.json()
    assert [invoice["invoice_number"] for invoice in payload] == ["F-002", "F-001"]
    assert all(invoice["lines"] for invoice in payload)


def test_invoice_list_filters_by_client_name_and_issue_date_range(database_path):
    user_id = create_user(database_path, "filters@example.com")
    alpha_client_id = create_client(database_path, user_id, "Alpha Conseil")
    beta_client_id = create_client(database_path, user_id, "Beta Services")

    with TestClient(app) as client:
        headers = auth_headers(user_id, "filters@example.com")
        alpha_january = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": alpha_client_id, "issue_date": "2024-01-15"},
            headers=headers,
        )
        alpha_march = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": alpha_client_id, "issue_date": "2024-03-10"},
            headers=headers,
        )
        beta_february = client.post(
            "/invoices",
            json={**INVOICE_PAYLOAD, "client_id": beta_client_id, "issue_date": "2024-02-05"},
            headers=headers,
        )

        by_client = client.get("/invoices?client_name=alpha", headers=headers)
        by_dates = client.get("/invoices?date_from=2024-02-01&date_to=2024-02-29", headers=headers)
        combined = client.get(
            "/invoices?client_name=alpha&date_from=2024-03-01&date_to=2024-03-31",
            headers=headers,
        )

    assert alpha_january.status_code == 201
    assert alpha_march.status_code == 201
    assert beta_february.status_code == 201
    assert [invoice["id"] for invoice in by_client.json()] == [alpha_march.json()["id"], alpha_january.json()["id"]]
    assert [invoice["id"] for invoice in by_dates.json()] == [beta_february.json()["id"]]
    assert [invoice["id"] for invoice in combined.json()] == [alpha_march.json()["id"]]
