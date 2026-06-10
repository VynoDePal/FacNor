import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

# Note: We are relying on the 'client' fixture from conftest.py

def test_create_client(client):
    payload = {
        "name": "New Client",
        "email": "new@example.com",
        "address": "456 New St",
        "vat_number": "FR987654321",
        "is_business": True
    }
    response = client.post("/clients/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["vat_number"] == payload["vat_number"]
    assert data["is_business"] == payload["is_business"]

def test_read_clients(client):
    # Create some clients
    client.post("/clients/", json={"name": "C1", "email": "c1@example.com"})
    client.post("/clients/", json={"name": "C2", "email": "c2@example.com"})
    
    response = client.get("/clients/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(c["name"] == "C1" for c in data)
    assert any(c["name"] == "C2" for c in data)

def test_read_client_by_id(client):
    payload = {"name": "Detail Client", "email": "detail@example.com"}
    create_res = client.post("/clients/", json=payload)
    client_id = create_res.json()["id"]
    
    response = client.get(f"/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Client"

def test_update_client(client):
    payload = {"name": "Old Name", "email": "old@example.com"}
    create_res = client.post("/clients/", json=payload)
    client_id = create_res.json()["id"]
    
    update_payload = {"name": "New Name", "is_business": True}
    response = client.put(f"/clients/{client_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["is_business"] is True
    assert data["email"] == "old@example.com"

def test_delete_client(client):
    payload = {"name": "To Delete", "email": "delete@example.com"}
    create_res = client.post("/clients/", json=payload)
    client_id = create_res.json()["id"]
    
    response = client.delete(f"/clients/{client_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_res = client.get(f"/clients/{client_id}")
    assert get_res.status_code == 404
