from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from main import app


def register_user(api: TestClient, email: str = "workflow@example.com") -> dict:
    response = api.post(
        "/auth/register",
        json={
            "email": email,
            "password": "MotDePasse123",
            "full_name": "Marie Workflow",
            "company_name": "Workflow SAS",
            "company_siren": "123456789",
            "company_vat_number": "FR00123456789",
        },
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(token_payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_payload['access_token']}"}


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_authenticated_business_workflow_covers_client_invoice_and_pdf_export(database_path):
    with TestClient(app) as api:
        registration = register_user(api)
        headers = auth_headers(registration)

        me = api.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "workflow@example.com"

        login = api.post(
            "/auth/login",
            json={"email": " WORKFLOW@example.com ", "password": "MotDePasse123"},
        )
        assert login.status_code == 200
        assert login.json()["token_type"] == "bearer"

        created_client = api.post(
            "/clients",
            json={
                "client_type": "B2B",
                "name": "  Alpha Workflow  ",
                "email": "contact@alpha.example",
                "address_line1": "10 rue des Tests",
                "postal_code": "75002",
                "city": "Paris",
                "siren": "987654321",
                "vat_number": "FR00987654321",
                "contact_full_name": "Alice Client",
            },
            headers=headers,
        )
        assert created_client.status_code == 201
        client_payload = created_client.json()
        assert client_payload["name"] == "Alpha Workflow"
        assert client_payload["client_type"] == "B2B"

        updated_client = api.patch(
            f"/clients/{client_payload['id']}",
            json={"phone": "+33123456789", "city": "Lyon"},
            headers=headers,
        )
        assert updated_client.status_code == 200
        assert updated_client.json()["phone"] == "+33123456789"
        assert updated_client.json()["city"] == "Lyon"

        client_list = api.get("/clients", headers=headers)
        assert client_list.status_code == 200
        assert [client["id"] for client in client_list.json()] == [client_payload["id"]]

        invoice = api.post(
            "/invoices",
            json={
                "client_id": client_payload["id"],
                "issue_date": "2024-06-15",
                "due_date": "2024-07-15",
                "legal_notice": "Indemnité forfaitaire de recouvrement de 40 euros.",
                "lines": [
                    {
                        "description": "Audit conformité",
                        "quantity": "2",
                        "unit_price_excluding_tax": "250.00",
                        "vat_rate": "20",
                    },
                    {
                        "description": "Support facturation",
                        "quantity": "1.5",
                        "unit_price_excluding_tax": "80.00",
                        "vat_rate": "10",
                    },
                ],
            },
            headers=headers,
        )
        assert invoice.status_code == 201
        invoice_payload = invoice.json()
        assert invoice_payload["invoice_number"] == "F-001"
        assert invoice_payload["total_excluding_tax"] == "620.00"
        assert invoice_payload["total_tax"] == "112.00"
        assert invoice_payload["total_including_tax"] == "732.00"

        listed_invoices = api.get("/invoices?client_name=alpha&date_from=2024-06-01&date_to=2024-06-30", headers=headers)
        assert listed_invoices.status_code == 200
        assert [item["id"] for item in listed_invoices.json()] == [invoice_payload["id"]]

        updated_invoice = api.patch(
            f"/invoices/{invoice_payload['id']}",
            json={"status": "issued"},
            headers=headers,
        )
        assert updated_invoice.status_code == 200
        assert updated_invoice.json()["status"] == "issued"

        pdf = api.get(f"/invoices/{invoice_payload['id']}/pdf", headers=headers)
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert "facture-F-001.pdf" in pdf.headers["content-disposition"]
        pdf_text = extract_pdf_text(pdf.content)
        assert "Facture F-001" in pdf_text
        assert "Workflow SAS" in pdf_text
        assert "Alpha Workflow" in pdf_text
        assert "Audit conformité" in pdf_text
        assert "732.00 EUR" in pdf_text


def test_invalid_and_unauthorized_api_requests_are_rejected(database_path):
    with TestClient(app) as api:
        registration = register_user(api, "negative-workflow@example.com")
        headers = auth_headers(registration)

        invalid_login = api.post(
            "/auth/login",
            json={"email": "negative-workflow@example.com", "password": "mauvais-secret"},
        )
        assert invalid_login.status_code == 401

        unauthenticated_clients = api.get("/clients")
        assert unauthenticated_clients.status_code == 401

        invalid_client = api.post(
            "/clients",
            json={
                "client_type": "B2B",
                "name": "Entreprise sans SIREN",
                "address_line1": "1 rue Invalide",
                "postal_code": "75001",
                "city": "Paris",
            },
            headers=headers,
        )
        assert invalid_client.status_code == 422

        missing_invoice_client = api.post(
            "/invoices",
            json={
                "client_id": 9999,
                "issue_date": "2024-06-15",
                "lines": [
                    {
                        "description": "Prestation impossible",
                        "quantity": "1",
                        "unit_price_excluding_tax": "100",
                        "vat_rate": "20",
                    }
                ],
            },
            headers=headers,
        )
        assert missing_invoice_client.status_code == 404
