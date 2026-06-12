import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from main import app
import os

TEST_DATABASE_URL = "sqlite:///./test_pdf_export.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# No module-level override here to avoid conflicts with other test files

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    with open("schema.sql", "r") as f:
        schema = f.read()
    with engine.connect() as connection:
        connection.connection.executescript(schema)
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)

def get_auth_header(username="testuser", password="testpassword"):
    client.post("/auth/register", json={
        "username": username,
        "password": password,
        "email": f"{username}@example.com"
    })
    response = client.post("/auth/login", data={
        "username": username,
        "password": password
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_export_invoice_pdf():
    auth_header = get_auth_header()
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

def test_export_invoice_pdf_not_found():
    auth_header = get_auth_header()
    response = client.get("/invoices/999/pdf", headers=auth_header)
    assert response.status_code == 404

def test_export_invoice_pdf_unauthorized():
    # User 1
    auth_header1 = get_auth_header("user1", "pass1")
    # User 2
    auth_header2 = get_auth_header("user2", "pass2")
    
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
