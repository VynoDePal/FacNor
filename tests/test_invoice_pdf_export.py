from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.auth import create_access_token
from app.database import connect
from main import app


def create_user(database_path, email="pdf-owner@example.com"):
    with connect(database_path) as connection:
        return connection.execute(
            """
            INSERT INTO users (
                email, password_hash, full_name, company_name, company_siren, company_vat_number
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, "hash", "Jeanne Émettrice", "Émetteur SAS", "123456789", "FR12123456789"),
        ).lastrowid


def create_client(database_path, user_id):
    with connect(database_path) as connection:
        return connection.execute(
            """
            INSERT INTO clients (
                user_id, client_type, name, email, phone, address_line1, address_line2,
                postal_code, city, country, siren, vat_number, contact_full_name
            ) VALUES (?, 'B2B', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "Client PDF SARL",
                "contact@client-pdf.test",
                "0102030405",
                "10 avenue des Tests",
                "Bâtiment A",
                "75001",
                "Paris",
                "France",
                "987654321",
                "FR98987654321",
                "Paul Client",
            ),
        ).lastrowid


def auth_headers(user_id, email="pdf-owner@example.com"):
    return {"Authorization": f"Bearer {create_access_token(user_id, email)}"}


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() for page in reader.pages)


def test_authenticated_user_can_export_invoice_as_pdf(database_path):
    user_id = create_user(database_path)
    client_id = create_client(database_path, user_id)

    with TestClient(app) as client:
        create_response = client.post(
            "/invoices",
            json={
                "client_id": client_id,
                "issue_date": "2024-05-01",
                "due_date": "2024-05-31",
                "legal_notice": "Paiement par virement sous 30 jours.",
                "lines": [
                    {
                        "description": "Audit de conformité",
                        "quantity": "1",
                        "unit_price_excluding_tax": "500",
                        "vat_rate": "20",
                    },
                    {
                        "description": "Accompagnement facturation",
                        "quantity": "2",
                        "unit_price_excluding_tax": "150",
                        "vat_rate": "10",
                    },
                ],
            },
            headers=auth_headers(user_id),
        )
        invoice_id = create_response.json()["id"]

        response = client.get(f"/invoices/{invoice_id}/pdf", headers=auth_headers(user_id))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="facture-F-001.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")

    text = extract_pdf_text(response.content)
    assert "Facture F-001" in text
    assert "Émetteur SAS" in text
    assert "Client PDF SARL" in text
    assert "SIREN: 123456789" in text
    assert "SIREN: 987654321" in text
    assert "Audit de conformité" in text
    assert "Accompagnement facturation" in text
    assert "Total HT" in text
    assert "800.00 EUR" in text
    assert "Total TVA" in text
    assert "130.00 EUR" in text
    assert "Total TTC" in text
    assert "930.00 EUR" in text
    assert "Paiement par virement sous 30 jours." in text


def test_invoice_pdf_export_is_scoped_to_authenticated_user(database_path):
    first_user_id = create_user(database_path, "first-pdf@example.com")
    second_user_id = create_user(database_path, "second-pdf@example.com")
    client_id = create_client(database_path, first_user_id)

    with TestClient(app) as client:
        create_response = client.post(
            "/invoices",
            json={
                "client_id": client_id,
                "issue_date": "2024-05-01",
                "lines": [
                    {
                        "description": "Prestation protégée",
                        "quantity": "1",
                        "unit_price_excluding_tax": "100",
                        "vat_rate": "20",
                    }
                ],
            },
            headers=auth_headers(first_user_id, "first-pdf@example.com"),
        )
        invoice_id = create_response.json()["id"]

        response = client.get(
            f"/invoices/{invoice_id}/pdf",
            headers=auth_headers(second_user_id, "second-pdf@example.com"),
        )

    assert response.status_code == 404
