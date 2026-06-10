import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}

def test_create_client(client):
    payload = {
        "name": "Client Test",
        "email": "test@example.com",
        "address": "123 Test St",
        "vat_number": "FR123456789",
        "is_business": True
    }
    response = client.post("/clients/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["vat_number"] == payload["vat_number"]
    assert "id" in data

def test_read_clients(client):
    # Create a few clients
    client.post("/clients/", json={"name": "Client 1", "email": "c1@example.com"})
    client.post("/clients/", json={"name": "Client 2", "email": "c2@example.com"})
    
    response = client.get("/clients/")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_read_client_by_id(client):
    payload = {"name": "Client Detail", "email": "detail@example.com"}
    create_res = client.post("/clients/", json=payload)
    client_id = create_res.json()["id"]
    
    response = client.get(f"/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Client Detail"

def test_read_client_not_found(client):
    response = client.get("/clients/999")
    assert response.status_code == 404

def test_update_client(client):
    payload = {"name": "Original Name", "email": "orig@example.com"}
    create_res = client.post("/clients/", json=payload)
    client_id = create_res.json()["id"]
    
    update_payload = {"name": "Updated Name"}
    response = client.put(f"/clients/{client_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["email"] == "orig@example.com"

def test_update_client_not_found(client):
    response = client.put("/clients/999", json={"name": "No One"})
    assert response.status_code == 404

def test_delete_client(client):
    payload = {"name": "To Delete", "email": "delete@example.com"}
    create_res = client.post("/clients/", json=payload)
    client_id = create_res.json()["id"]
    
    response = client.delete(f"/clients/{client_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_res = client.get(f"/clients/{client_id}")
    assert get_res.status_code == 404

def test_delete_client_not_found(client):
    response = client.delete("/clients/999")
    assert response.status_code == 404
