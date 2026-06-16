from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.db import create_invoice
from app.pdf import generate_invoice_pdf


def test_generate_invoice_pdf_contains_legal_invoice_data(
    db: sqlite3.Connection, sample_user_and_client: tuple[int, int]
) -> None:
    user_id, client_id = sample_user_and_client
    invoice = create_invoice(
        db,
        user_id=user_id,
        client_id=client_id,
        issue_date="2025-01-15",
        due_date="2025-02-15",
        lines=[
            {
                "description": "Audit conformite facturation",
                "quantity": 2,
                "unit_price_excluding_tax": 15000,
                "vat_rate": 20,
            }
        ],
    )

    pdf = generate_invoice_pdf(db, invoice["id"])

    assert pdf is not None
    assert pdf.startswith(b"%PDF-1.4")
    assert b"Facture FAC-000001" in pdf
    assert b"Emetteur" in pdf
    assert b"FacNor Conseil" in pdf
    assert b"Client SAS" in pdf
    assert b"Date d'emission : 2025-01-15" in pdf
    assert b"Audit conformite facturation" in pdf
    assert b"Total TTC : 360.00 EUR" in pdf
    assert b"Mentions legales" in pdf


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secret",
            "full_name": "API User",
            "company_name": "FacNor API",
            "siren": "123456789",
            "vat_number": "FRAB123456789",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_invoice(client: TestClient, headers: dict[str, str]) -> int:
    client_response = client.post(
        "/clients",
        headers=headers,
        json={
            "name": "Client PDF",
            "address": "8 rue du PDF",
            "postal_code": "44000",
            "city": "Nantes",
            "siren": "987654321",
            "vat_number": "FRZZ987654321",
        },
    )
    assert client_response.status_code == 201
    invoice_response = client.post(
        "/invoices",
        headers=headers,
        json={
            "client_id": client_response.json()["id"],
            "issue_date": "2025-03-01",
            "lines": [
                {
                    "description": "Export PDF",
                    "quantity": 1,
                    "unit_price_excluding_tax": 9900,
                    "vat_rate": 20,
                }
            ],
        },
    )
    assert invoice_response.status_code == 201
    return int(invoice_response.json()["id"])


def test_authenticated_user_can_download_own_invoice_pdf(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-pdf.db'}")

    from app.main import app

    with TestClient(app) as client:
        auth = _register(client, "pdf-owner@example.test")
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        invoice_id = _create_invoice(client, headers)

        response = client.get(f"/invoices/{invoice_id}/pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "facture-FAC-000001.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-1.4")
    assert b"Client PDF" in response.content
    assert b"Export PDF" in response.content


def test_user_cannot_download_another_users_invoice_pdf(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'facnor-pdf-ownership.db'}")

    from app.main import app

    with TestClient(app) as client:
        owner = _register(client, "pdf-owner-2@example.test")
        other = _register(client, "pdf-other@example.test")
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        invoice_id = _create_invoice(client, owner_headers)

        response = client.get(f"/invoices/{invoice_id}/pdf", headers=other_headers)

    assert response.status_code == 404
