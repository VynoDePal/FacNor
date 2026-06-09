import pytest
from app.core.database import get_db

def test_create_client(client):
    response = client.post(
        "/clients/",
        json={"name": "Test Client", "email": "test@example.com", "address": "123 Test St", "vat_number": "FR123456789", "siren": "123456789"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["siren"] == "123456789"

def test_read_client(client):
    # Create a client first
    response = client.post(
        "/clients/",
        json={"name": "Read Client", "email": "read@example.com", "address": "456 Read Ave", "vat_number": "FR987654321", "siren": "987654321"}
    )
    client_id = response.json()["id"]
    
    # Now read it
    response = client.get(f"/clients/{client_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Read Client"

def test_update_client(client):
    # Create a client first
    response = client.post(
        "/clients/",
        json={"name": "Update Client", "email": "update@example.com", "address": "789 Update Rd", "vat_number": "FR111222333", "siren": "111222333"}
    )
    client_id = response.json()["id"]
    
    # Now update it
    response = client.put(
        f"/clients/{client_id}",
        json={"name": "Updated Name"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"

def test_delete_client(client):
    # Create a client first
    response = client.post(
        "/clients/",
        json={"name": "Delete Client", "email": "delete@example.com", "address": "000 Delete Ln", "vat_number": "FR000000000", "siren": "000000000"}
    )
    client_id = response.json()["id"]
    
    # Now delete it
    response = client.delete(f"/clients/{client_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    response = client.get(f"/clients/{client_id}")
    assert response.status_code == 404
