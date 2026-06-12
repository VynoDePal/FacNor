import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from main import app
import sqlite3
import os

# Use a file-based database for tests to avoid in-memory connection issues
TEST_DATABASE_URL = "sqlite:///./test_facnor.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    # Create schema using schema.sql
    with open("schema.sql", "r") as f:
        schema = f.read()
    
    with engine.connect() as connection:
        connection.connection.executescript(schema)
    
    yield
    Base.metadata.drop_all(bind=engine)

def get_auth_header(username="testuser", password="testpassword"):
    # Register user
    client.post("/auth/register", json={
        "username": username,
        "password": password,
        "email": f"{username}@example.com"
    })
    # Login user
    response = client.post("/auth/login", data={
        "username": username,
        "password": password
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_auth_register():
    response = client.post("/auth/register", json={
        "username": "reguser",
        "password": "regpassword",
        "email": "reg@example.com"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "reguser"

def test_auth_login():
    client.post("/auth/register", json={
        "username": "loginuser",
        "password": "loginpassword",
        "email": "login@example.com"
    })
    response = client.post("/auth/login", data={
        "username": "loginuser",
        "password": "loginpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_create_client():
    auth_header = get_auth_header()
    response = client.post("/clients/", json={
        "name": "Client Test",
        "address": "123 Test St",
        "email": "test@client.com",
        "phone": "0123456789",
        "siren": "123456789",
        "tva_number": "FR123456789",
        "is_company": True
    }, headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Client Test"
    assert data["siren"] == "123456789"

def test_create_invoice():
    auth_header = get_auth_header()
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "Client Invoice",
        "is_company": False
    }, headers=auth_header)
    client_id = client_resp.json()["id"]
    
    response = client.post("/invoices/", json={
        "invoice_number": "INV-2023-001",
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "date_due": "2023-10-15",
        "status": "draft",
        "notes": "Test invoice",
        "lines": [
            {"description": "Service A", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 20.0},
            {"description": "Service B", "quantity": 2.0, "unit_price_ht": 50.0, "vat_rate": 20.0}
        ]
    }, headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["invoice_number"] == "INV-2023-001"
    assert len(data["lines"]) == 2

def test_read_client():
    auth_header = get_auth_header()
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "Client Read Test",
        "is_company": False
    }, headers=auth_header)
    client_id = client_resp.json()["id"]
    
    # Read client
    response = client.get(f"/clients/{client_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["name"] == "Client Read Test"

def test_read_client_not_found():
    auth_header = get_auth_header()
    response = client.get("/clients/999", headers=auth_header)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"

def test_update_client():
    auth_header = get_auth_header()
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "Client Update Test",
        "is_company": False
    }, headers=auth_header)
    client_id = client_resp.json()["id"]
    
    # Update client
    update_data = {
        "name": "Client Updated Name",
        "address": "New Address",
        "email": "updated@client.com",
        "phone": "0987654321",
        "siren": "987654321",
        "tva_number": "FR987654321",
        "is_company": True
    }
    response = client.put(f"/clients/{client_id}", json=update_data, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["name"] == "Client Updated Name"
    assert response.json()["is_company"] is True
    
    # Verify update
    read_resp = client.get(f"/clients/{client_id}", headers=auth_header)
    assert read_resp.json()["name"] == "Client Updated Name"

def test_update_client_not_found():
    auth_header = get_auth_header()
    response = client.put("/clients/999", json={"name": "Non existent"}, headers=auth_header)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"

def test_delete_client():
    auth_header = get_auth_header()
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "Client Delete Test",
        "is_company": False
    }, headers=auth_header)
    client_id = client_resp.json()["id"]
    
    # Delete client
    response = client.delete(f"/clients/{client_id}", headers=auth_header)
    assert response.status_code == 204
    
    # Verify deletion
    read_resp = client.get(f"/clients/{client_id}", headers=auth_header)
    assert read_resp.status_code == 404

def test_delete_client_not_found():
    auth_header = get_auth_header()
    response = client.delete("/clients/999", headers=auth_header)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"


def test_read_invoice():
    auth_header = get_auth_header()
    # Create client
    client_resp = client.post("/clients/", json={"name": "Client Read Invoice", "is_company": False}, headers=auth_header)
    client_id = client_resp.json()["id"]
    
    # Create invoice
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header)
    invoice_id = invoice_resp.json()["id"]
    
    # Read invoice
    response = client.get(f"/invoices/{invoice_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["client_id"] == client_id

def test_update_invoice():
    auth_header = get_auth_header()
    # Create client
    client_resp = client.post("/clients/", json={"name": "Client Update Invoice", "is_company": False}, headers=auth_header)
    client_id = client_resp.json()["id"]
    
    # Create invoice
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header)
    invoice_id = invoice_resp.json()["id"]
    
    # Update invoice
    update_data = {
        "client_id": client_id,
        "date_issued": "2023-10-02",
        "status": "sent",
        "notes": "Updated notes",
        "lines": [{"description": "Item 1 Updated", "quantity": 2.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }
    response = client.put(f"/invoices/{invoice_id}", json=update_data, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["date_issued"] == "2023-10-02"
    assert response.json()["status"] == "sent"
    assert response.json()["notes"] == "Updated notes"
    assert len(response.json()["lines"]) == 1
    assert response.json()["lines"][0]["description"] == "Item 1 Updated"
    assert response.json()["lines"][0]["quantity"] == 2.0

def test_delete_invoice():
    auth_header = get_auth_header()
    # Create client
    client_resp = client.post("/clients/", json={"name": "Client Delete Invoice", "is_company": False}, headers=auth_header)
    client_id = client_resp.json()["id"]
    
    # Create invoice
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header)
    invoice_id = invoice_resp.json()["id"]
    
    # Delete invoice
    response = client.delete(f"/invoices/{invoice_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["detail"] == "Invoice deleted successfully"
    
    # Verify deletion
    read_resp = client.get(f"/invoices/{invoice_id}", headers=auth_header)
    assert read_resp.status_code == 404

def test_invoice_access_control():
    # User 1
    auth_header1 = get_auth_header("user1", "pass1")
    # User 2
    auth_header2 = get_auth_header("user2", "pass2")
    
    # User 1 creates a client and invoice
    client_resp = client.post("/clients/", json={"name": "User1 Client", "is_company": False}, headers=auth_header1)
    client_id = client_resp.json()["id"]
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header1)
    invoice_id = invoice_resp.json()["id"]
    
    # User 2 tries to read User 1's invoice
    response = client.get(f"/invoices/{invoice_id}", headers=auth_header2)
    assert response.status_code == 403
    
    # User 2 tries to update User 1's invoice
    update_data = {
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }
    response = client.put(f"/invoices/{invoice_id}", json=update_data, headers=auth_header2)
    assert response.status_code == 403
    
    # User 2 tries to delete User 1's invoice
    response = client.delete(f"/invoices/{invoice_id}", headers=auth_header2)
    assert response.status_code == 403

