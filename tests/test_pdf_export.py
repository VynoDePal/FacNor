from tests.test_api import auth_headers, register_user
from tests.test_invoices import create_owned_client


def create_invoice(client, headers, client_id):
    response = client.post(
        "/invoices",
        headers=headers,
        json={
            "client_id": client_id,
            "issue_date": "2025-02-03",
            "due_date": "2025-03-05",
            "lines": [
                {"description": "Prestation conseil", "quantity": 2, "unit_price": 100, "tax_rate": 20},
                {"description": "Frais de dossier", "quantity": 1, "unit_price": 50, "tax_rate": 10},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_invoice_pdf_export_contains_required_invoice_information(client):
    user = register_user(client, "pdf-owner@example.com")
    headers = auth_headers(user["access_token"])
    owned_client = create_owned_client(client, user["access_token"], "Client PDF")
    invoice = create_invoice(client, headers, owned_client["id"])

    response = client.get(f"/invoices/{invoice['id']}/pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="facture-FAC-2025-0001.pdf"'
    assert response.content.startswith(b"%PDF-1.4")
    pdf_text = response.content.decode("latin-1")
    assert "Emetteur: Ada Lovelace" in pdf_text
    assert "Email emetteur: pdf-owner@example.com" in pdf_text
    assert "Client: Client PDF" in pdf_text
    assert "Adresse client: 1 rue de Paris" in pdf_text
    assert "Numero: FAC-2025-0001" in pdf_text
    assert "Date: 2025-02-03" in pdf_text
    assert "Prestation conseil" in pdf_text
    assert "Frais de dossier" in pdf_text
    assert "20%" in pdf_text
    assert "10%" in pdf_text
    assert "Total HT: 250.00 EUR" in pdf_text
    assert "Total TVA: 45.00 EUR" in pdf_text
    assert "Total TTC: 295.00 EUR" in pdf_text


def test_invoice_pdf_export_is_scoped_to_authenticated_owner(client):
    owner = register_user(client, "pdf-owner-private@example.com")
    attacker = register_user(client, "pdf-attacker@example.com")
    owner_headers = auth_headers(owner["access_token"])
    attacker_headers = auth_headers(attacker["access_token"])
    owned_client = create_owned_client(client, owner["access_token"], "Client privé PDF")
    invoice = create_invoice(client, owner_headers, owned_client["id"])

    response = client.get(f"/invoices/{invoice['id']}/pdf", headers=attacker_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Invoice not found"}
