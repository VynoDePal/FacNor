import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Base

def test_create_invoice(client):
    # First create a client and a user (if needed by the API, but here user_id is required in InvoiceCreate)
    # Looking at app/main.py, create_user exists.
    user_payload = {"username": "testuser", "email": "test@user.com", "password": "password123"}
    user_res = client.post("/users/", json=user_payload)
    user_id = user_res.json()["id"]
    
    client_payload = {"name": "Invoice Client", "email": "client@example.com"}
    client_res = client.post("/clients/", json=client_payload)
    client_id = client_res.json()["id"]
    
    invoice_payload = {
        "date": "2023-10-01T10:00:00",
        "due_date": "2023-10-15T10:00:00",
        "client_id": client_id,
        "user_id": user_id,
        "total_ht": 0, # Should be calculated by backend
        "total_tva": 0, # Should be calculated by backend
        "total_ttc": 0, # Should be calculated by backend
        "status": "draft",
        "lines": [
            {"description": "Product 1", "quantity": 2, "unit_price": 100.0, "tax_rate": 20.0, "total_ht": 0, "total_tva": 0, "total_ttc": 0},
            {"description": "Product 2", "quantity": 1, "unit_price": 50.0, "tax_rate": 20.0, "total_ht": 0, "total_tva": 0, "total_ttc": 0}
        ]
    }
    
    response = client.post("/invoices/", json=invoice_payload)
    assert response.status_code == 201
    data = response.json()
    
    # Calculations check:
    # Line 1: 2 * 100 = 200 HT, 200 * 0.2 = 40 TVA, 240 TTC
    # Line 2: 1 * 50 = 50 HT, 50 * 0.2 = 10 TVA, 60 TTC
    # Total: 250 HT, 50 TVA, 300 TTC
    
    assert data["total_ht"] == 250.0
    assert data["total_tva"] == 50.0
    assert data["total_ttc"] == 300.0
    assert len(data["lines"]) == 2
    assert data["lines"][0]["total_ttc"] == 240.0
    assert data["lines"][1]["total_ttc"] == 60.0
    assert "invoice_number" in data

def test_read_invoice(client):
    # Setup: create invoice
    user_payload = {"username": "readuser", "email": "read@user.com", "password": "password123"}
    user_res = client.post("/users/", json=user_payload)
    user_id = user_res.json()["id"]
    
    client_payload = {"name": "Read Client", "email": "read@client.com"}
    client_res = client.post("/clients/", json=client_payload)
    client_id = client_res.json()["id"]
    
    invoice_payload = {
        "date": "2023-10-01T10:00:00",
        "client_id": client_id,
        "user_id": user_id,
        "total_ht": 0, "total_tva": 0, "total_ttc": 0,
        "lines": [{"description": "Item", "quantity": 1, "unit_price": 10, "tax_rate": 20, "total_ht": 0, "total_tva": 0, "total_ttc": 0}]
    }
    create_res = client.post("/invoices/", json=invoice_payload)
    invoice_id = create_res.json()["id"]
    
    response = client.get(f"/invoices/{invoice_id}")
    assert response.status_code == 200
    assert response.json()["id"] == invoice_id

def test_update_invoice(client):
    # Setup: create invoice
    user_payload = {"username": "updateuser", "email": "update@user.com", "password": "password123"}
    user_res = client.post("/users/", json=user_payload)
    user_id = user_res.json()["id"]
    
    client_payload = {"name": "Update Client", "email": "update@client.com"}
    client_res = client.post("/clients/", json=client_payload)
    client_id = client_res.json()["id"]
    
    invoice_payload = {
        "date": "2023-10-01T10:00:00",
        "client_id": client_id,
        "user_id": user_id,
        "total_ht": 0, "total_tva": 0, "total_ttc": 0,
        "lines": [{"description": "Item", "quantity": 1, "unit_price": 10, "tax_rate": 20, "total_ht": 0, "total_tva": 0, "total_ttc": 0}]
    }
    create_res = client.post("/invoices/", json=invoice_payload)
    invoice_id = create_res.json()["id"]
    
    update_payload = {"status": "paid"}
    response = client.put(f"/invoices/{invoice_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "paid"

def test_delete_invoice(client):
    # Setup: create invoice
    user_payload = {"username": "deluser", "email": "del@user.com", "password": "password123"}
    user_res = client.post("/users/", json=user_payload)
    user_id = user_res.json()["id"]
    
    client_payload = {"name": "Del Client", "email": "del@client.com"}
    client_res = client.post("/clients/", json=client_payload)
    client_id = client_res.json()["id"]
    
    invoice_payload = {
        "date": "2023-10-01T10:00:00",
        "client_id": client_id,
        "user_id": user_id,
        "total_ht": 0, "total_tva": 0, "total_ttc": 0,
        "lines": [{"description": "Item", "quantity": 1, "unit_price": 10, "tax_rate": 20, "total_ht": 0, "total_tva": 0, "total_ttc": 0}]
    }
    create_res = client.post("/invoices/", json=invoice_payload)
    invoice_id = create_res.json()["id"]
    
    response = client.delete(f"/invoices/{invoice_id}")
    assert response.status_code == 204
    
    get_res = client.get(f"/invoices/{invoice_id}")
    assert get_res.status_code == 404
