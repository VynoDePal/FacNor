import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

def create_test_user(client):
    user_payload = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    }
    client.post("/users/", json=user_payload)
    response = client.post("/token", data={"username": "testuser", "password": "testpassword"})
    return response.json()["access_token"]

def create_test_client(client):
    client_payload = {
        "name": "Test Client",
        "email": "client@example.com",
        "address": "123 Client St",
        "vat_number": "FR123456789",
        "is_business": True
    }
    response = client.post("/clients/", json=client_payload)
    return response.json()["id"]

def test_create_invoice(client, db):
    token = create_test_user(client)
    client_id = create_test_client(client)
    
    invoice_payload = {
        "date": "2023-10-01T10:00:00",
        "due_date": "2023-10-15T10:00:00",
        "client_id": client_id,
        "user_id": 1, # This should probably be obtained from the token
        "total_ht": 100.0,
        "total_tva": 20.0,
        "total_ttc": 120.0,
        "status": "draft",
        "lines": [
            {"description": "Item 1", "quantity": 1, "unit_price": 100.0, "tax_rate": 20.0, "total_ht": 100.0, "total_tva": 20.0, "total_ttc": 120.0}
        ]
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/invoices/", json=invoice_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["invoice_number"].startswith("INV-")
    assert data["total_ttc"] == 120.0

def test_get_invoices_filtering(client, db):
    token = create_test_user(client)
    client_id_1 = create_test_client(client)
    client_id_2 = create_test_client(client) # Actually we can't call create_test_client twice with the same name if it was used in other tests but we are in a fresh DB per test
    
    # But create_test_client creates "Test Client". Let's just use a payload directly.
    def create_invoice_helper(c, t, cid, date_str, total):
        payload = {
            "date": date_str,
            "due_date": "2023-12-31T10:00:00",
            "client_id": cid,
            "user_id": 1,
            "total_ht": total,
            "total_tva": total * 0.2,
            "total_ttc": total * 1.2,
            "status": "draft",
            "lines": []
        }
        return c.post("/invoices/", json=payload, headers={"Authorization": f"Bearer {t}"})

    # Create invoices
    create_invoice_helper(client, token, client_id_1, "2023-01-01T10:00:00", 100.0)
    create_invoice_helper(client, token, client_id_1, "2023-02-01T10:00:00", 200.0)
    create_invoice_helper(client, token, client_id_2, "2023-03-01T10:00:00", 300.0)

    # Filter by client
    response = client.get("/invoices/?client_id=" + str(client_id_1), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Filter by date range
    response = client.get("/invoices/?start_date=2023-01-01T00:00:00&end_date=2023-02-15T00:00:00", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 2

    # No filter
    response = client.get("/invoices/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 3

def test_get_invoice_by_id(client, db):
    token = create_test_user(client)
    client_id = create_test_client(client)
    
    invoice_payload = {
        "date": "2023-10-01T10:00:00",
        "due_date": "2023-10-15T10:00:00",
        "client_id": client_id,
        "user_id": 1,
        "total_ht": 100.0,
        "total_tva": 20.0,
        "total_ttc": 120.0,
        "status": "draft",
        "lines": []
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    create_res = client.post("/invoices/", json=invoice_payload, headers=headers)
    invoice_id = create_res.json()["id"]

    response = client.get(f"/invoices/{invoice_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == invoice_id

def test_delete_invoice(client, db):
    token = create_test_user(client)
    client_id = create_test_client(client)
    
    invoice_payload = {
        "date": "2023-10-01T10:00:00",
        "due_date": "2023-10-15T10:00:00",
        "client_id": client_id,
        "user_id": 1,
        "total_ht": 100.0,
        "total_tva": 20.0,
        "total_ttc": 120.0,
        "status": "draft",
        "lines": []
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    create_res = client.post("/invoices/", json=invoice_payload, headers=headers)
    invoice_id = create_res.json()["id"]

    response = client.delete(f"/invoices/{invoice_id}", headers=headers)
    assert response.status_code == 204

    # Verify it's gone
    get_res = client.get(f"/invoices/{invoice_id}", headers=headers)
    assert get_res.status_code == 404
