import pytest

def test_export_invoice_pdf(client, auth_header):
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "PDF Client",
        "address": "123 PDF Ave",
        "email": "pdf@client.com",
        "siren": "123456789",
        "tva_number": "FR123456789",
        "is_company": True
    }, headers=auth_header)
    client_id = client_resp.json()["id"]

    # Create invoice
    invoice_resp = client.post("/invoices/", json={
        "invoice_number": "PDF-2023-001",
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [
            {"description": "PDF Service", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 20.0},
            {"description": "Another Service", "quantity": 2.0, "unit_price_ht": 50.0, "vat_rate": 20.0}
        ]
    }, headers=auth_header)
    invoice_id = invoice_resp.json()["id"]

    # Export PDF
    response = client.get(f"/invoices/{invoice_id}/pdf", headers=auth_header)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=invoice_PDF-2023-001.pdf" in response.headers["content-disposition"]
    assert len(response.content) > 0

def test_export_invoice_pdf_not_found(client, auth_header):
    response = client.get("/invoices/999/pdf", headers=auth_header)
    assert response.status_code == 404

def test_export_invoice_pdf_unauthorized(client):
    # User 1
    client.post("/auth/register", json={"username": "u1", "password": "p1", "email": "u1@example.com"})
    response1 = client.post("/auth/login", data={"username": "u1", "password": "p1"})
    auth_header1 = {"Authorization": f"Bearer {response1.json()['access_token']}"}

    # User 2
    client.post("/auth/register", json={"username": "u2", "password": "p2", "email": "u2@example.com"})
    response2 = client.post("/auth/login", data={"username": "u2", "password": "p2"})
    auth_header2 = {"Authorization": f"Bearer {response2.json()['access_token']}"}

    # User 1 creates client and invoice
    client_resp = client.post("/clients/", json={"name": "U1 Client", "is_company": False}, headers=auth_header1)
    client_id = client_resp.json()["id"]
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 20.0}]
    }, headers=auth_header1)
    invoice_id = invoice_resp.json()["id"]

    # User 2 tries to export User 1's invoice
    response = client.get(f"/invoices/{invoice_id}/pdf", headers=auth_header2)
    assert response.status_code == 403
