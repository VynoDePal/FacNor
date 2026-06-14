from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str = "pdf-owner@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "correct-password", "full_name": "FacNor SARL"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_client(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/clients",
        headers=headers,
        json={
            "name": "Client PDF",
            "client_type": "individual",
            "email": "client.pdf@example.com",
            "address": "10 rue de Paris, 75001 Paris",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_invoice(client: TestClient, headers: dict[str, str], client_id: int) -> int:
    response = client.post(
        "/invoices",
        headers=headers,
        json={
            "client_id": client_id,
            "issue_date": "2024-01-15",
            "due_date": "2024-02-15",
            "status": "issued",
            "items": [
                {
                    "description": "Prestation PDF",
                    "quantity": "2",
                    "unit_price_excluding_tax": "100.00",
                    "vat_rate": "20",
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_export_invoice_pdf_returns_valid_pdf_for_owner(client: TestClient) -> None:
    headers = _auth_headers(client)
    client_id = _create_client(client, headers)
    invoice_id = _create_invoice(client, headers, client_id)

    response = client.get(f"/invoices/{invoice_id}/pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="FAC-000001.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    assert b"Facture FAC-000001" in response.content
    assert b"Client PDF" in response.content
    assert b"Prestation PDF" in response.content
    assert b"240.00 EUR" in response.content


def test_export_invoice_pdf_requires_authentication(client: TestClient) -> None:
    response = client.get("/invoices/1/pdf")

    assert response.status_code == 401


def test_export_invoice_pdf_is_limited_to_invoice_owner(client: TestClient) -> None:
    first_headers = _auth_headers(client, "pdf-a@example.com")
    second_headers = _auth_headers(client, "pdf-b@example.com")
    client_id = _create_client(client, first_headers)
    invoice_id = _create_invoice(client, first_headers, client_id)

    response = client.get(f"/invoices/{invoice_id}/pdf", headers=second_headers)

    assert response.status_code == 404
