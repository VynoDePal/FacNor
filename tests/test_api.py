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
