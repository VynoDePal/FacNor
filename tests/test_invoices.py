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

def test_filter_invoices_by_client(client):
    # Setup: create 2 clients and 2 invoices
    user_payload = {"username": "filteruser", "email": "filter@user.com", "password": "password123"}
    user_res = client.post("/users/", json=user_payload)
    user_id = user_res.json()["id"]

    c1_payload = {"name": "Client 1", "email": "c1@example.com"}
    c1_res = client.post("/clients/", json=c1_payload)
    c1_id = c1_res.json()["id"]

    c2_payload = {"name": "Client 2", "email": "c2@example.com"}
    c2_res = client.post("/clients/", json=c2_payload)
    c2_id = c2_res.json()["id"]

    invoice_payload1 = {
        "date": "2023-10-01T10:00:00",
        "client_id": c1_id,
        "user_id": user_id,
        "total_ht": 0, "total_tva": 0, "total_ttc": 0,
        "lines": [{"description": "Item 1", "quantity": 1, "unit_price": 10, "tax_rate": 20, "total_ht": 0, "total_tva": 0, "total_ttc": 0}]
    }
    client.post("/invoices/", json=invoice_payload1)

    invoice_payload2 = {
        "date": "2023-10-02T10:00:00",
        "client_id": c2_id,
        "user_id": user_id,
        "total_ht": 0, "total_tva": 0, "total_ttc": 0,
        "lines": [{"description": "Item 2", "quantity": 1, "unit_price": 10, "tax_rate": 20, "total_ht": 0, "total_tva": 0, "total_ttc": 0}]
    }
    client.post("/invoices/", json=invoice_payload2)

    # Filter by client 1
    response = client.get(f"/invoices/?client_id={c1_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["client_id"] == c1_id

    # Filter by client 2
    response = client.get(f"/invoices/?client_id={c2_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["client_id"] == c2_id

def test_filter_invoices_by_date(client):
    # Setup: create user and client
    user_payload = {"username": "datefilteruser", "email": "datefilter@user.com", "password": "password123"}
    user_res = client.post("/users/", json=user_payload)
    user_id = user_res.json()["id"]

    client_payload = {"name": "Date Client", "email": "date@client.com"}
    client_res = client.post("/clients/", json=client_payload)
    client_id = client_res.json()["id"]

    # Create invoices on different dates
    dates = ["2023-10-01T10:00:00", "2023-10-02T10:00:00", "2023-10-03T10:00:00"]
    for d in dates:
        invoice_payload = {
            "date": d,
            "client_id": client_id,
            "user_id": user_id,
            "total_ht": 0, "total_tva": 0, "total_ttc": 0,
            "lines": [{"description": "Item", "quantity": 1, "unit_price": 10, "tax_rate": 20, "total_ht": 0, "total_tva": 0, "total_ttc": 0}]
        }
        client.post("/invoices/", json=invoice_payload)

    # Filter by first date
    response = client.get("/invoices/?date=2023-10-01T10:00:00")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2023-10-01T10:00:00"

