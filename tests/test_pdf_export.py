import pytest
import datetime

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, get_db
from app.models.user import User
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.services.auth_service import AuthService
from pypdf import PdfReader
import io

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="hashed_password")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_client_obj(db_session, test_user):
    c = Client(user_id=test_user.id, name="Test Client", address="123 Rue de Paris", email="client@example.com")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c

@pytest.fixture
def test_invoice(db_session, test_user, test_client_obj):
    inv = Invoice(
        user_id=test_user.id,
        client_id=test_client_obj.id,
        invoice_number="FAC-2024-001",
        date=datetime.date(2024, 1, 1),
        status="draft"
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    
    item = InvoiceItem(
        invoice_id=inv.id,
        description="Consulting",
        quantity=1,
        unit_price_ht=100,
        vat_rate=20
    )
    db_session.add(item)
    db_session.commit()
    return inv

def get_token(username):
    # Mock login to get a token
    # In a real scenario, we would call /token, but for unit tests we can use AuthService
    return AuthService.create_access_token(data={"sub": username})

def test_pdf_content_compliance(test_invoice):
    from app.services.pdf_service import PDFService
    pdf_bytes = PDFService.generate_invoice_pdf(test_invoice)
    
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    assert "FACTURE" in text
    assert "FAC-2024-001" in text
    assert "Test Client" in text
    assert "Pénalités de retard : Taux légal en vigueur." in text
    assert "Indemnité forfaitaire pour frais de recouvrement : 40 €." in text
    assert "TVA acquittée sur les encaissements." in text

def test_export_pdf_endpoint(test_user, test_invoice):
    token = get_token(test_user.username)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(f"/invoices/{test_invoice.id}/pdf", headers=headers)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "invoice_FAC-2024-001.pdf" in response.headers["Content-Disposition"]
    
    # Also check the content of the downloaded PDF
    reader = PdfReader(io.BytesIO(response.content))
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    assert "FACTURE" in text
    assert "FAC-2024-001" in text
