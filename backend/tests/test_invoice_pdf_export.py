import re
import zlib
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.main import app

USER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "secure-password",
    "company_name": "FacNor SAS",
    "siren": "123456789",
    "vat_number": "FR12345678901",
    "address": "1 rue de Paris, 75000 Paris",
}

CLIENT_PAYLOAD = {
    "name": "Client Entreprise",
    "email": "contact@client.example",
    "client_type": "business",
    "siren": "987654321",
    "vat_number": "FR98765432100",
    "address": "2 avenue de Lyon, 69000 Lyon",
}

INVOICE_PAYLOAD = {
    "issue_date": "2025-01-15",
    "due_date": "2025-02-15",
    "items": [
        {
            "description": "Prestation de conseil",
            "quantity": "2.00",
            "unit_price_excluding_tax": "100.00",
            "vat_rate": "20.00",
        }
    ],
}


def test_invoice_pdf_export_contains_required_legal_information() -> None:
    with invoice_api() as client:
        headers = _auth_headers(client)
        client_id = _create_client(client, headers)
        invoice = client.post("/api/invoices", json=INVOICE_PAYLOAD | {"client_id": client_id}, headers=headers).json()

        response = client.get(f"/api/invoices/{invoice['id']}/pdf", headers=headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"] == 'attachment; filename="invoice-0001.pdf"'
        assert response.content.startswith(b"%PDF-1.4")
        text = _extract_pdf_text(response.content)
        for expected in [
            "Facture 0001",
            "Emetteur",
            "FacNor SAS",
            "SIREN: 123456789",
            "TVA intracommunautaire: FR12345678901",
            "Client Entreprise",
            "SIREN: 987654321",
            "TVA intracommunautaire: FR98765432100",
            "Numero de facture: 0001",
            "Date d'emission: 2025-01-15",
            "Date d'echeance: 2025-02-15",
            "Prestation de conseil",
            "Total HT: 200.00 EUR",
            "Total TVA: 40.00 EUR",
            "Total TTC: 240.00 EUR",
        ]:
            assert expected in text


def test_invoice_pdf_export_requires_authentication_and_ownership() -> None:
    with invoice_api() as client:
        owner_headers = _auth_headers(client)
        other_headers = _auth_headers(client, email="other@example.com")
        client_id = _create_client(client, owner_headers)
        invoice = client.post("/api/invoices", json=INVOICE_PAYLOAD | {"client_id": client_id}, headers=owner_headers).json()

        unauthenticated_response = client.get(f"/api/invoices/{invoice['id']}/pdf")
        other_user_response = client.get(f"/api/invoices/{invoice['id']}/pdf", headers=other_headers)

        assert unauthenticated_response.status_code == 401
        assert other_user_response.status_code == 404


def test_invoice_pdf_export_paginates_and_sanitizes_text() -> None:
    with invoice_api() as client:
        headers = _auth_headers(client)
        client_id = _create_client(client, headers)
        items = [
            {
                "description": f"Service étendu (phase \\ {index})",
                "quantity": "1.00",
                "unit_price_excluding_tax": "10.00",
                "vat_rate": "20.00",
            }
            for index in range(60)
        ]
        invoice = client.post(
            "/api/invoices",
            json=INVOICE_PAYLOAD | {"client_id": client_id, "items": items},
            headers=headers,
        ).json()

        response = client.get(f"/api/invoices/{invoice['id']}/pdf", headers=headers)

        assert response.status_code == 200
        assert b"/Count 2" in response.content
        text = _extract_pdf_text(response.content)
        assert "Service etendu \\(phase \\\\ 59\\)" in text
        assert "Total TTC: 720.00 EUR" in text


class invoice_api:
    def __enter__(self) -> TestClient:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def override_get_db() -> Generator[Session, None, None]:
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        return self.client

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        app.dependency_overrides.clear()


def _auth_headers(client: TestClient, email: str = USER_PAYLOAD["email"]) -> dict[str, str]:
    payload = USER_PAYLOAD | {"email": email}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_client(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/api/clients", json=CLIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    return int(response.json()["id"])


def _extract_pdf_text(pdf: bytes) -> str:
    streams = re.findall(rb"stream\n(.*?)\nendstream", pdf, re.DOTALL)
    assert streams
    decoded_streams = []
    for stream in streams:
        if stream.startswith(b"x\x9c"):
            stream = zlib.decompress(stream)
        decoded_streams.append(stream.decode("latin-1"))
    return "\n".join(decoded_streams)
