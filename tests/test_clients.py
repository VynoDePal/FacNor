from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_create_client_particulier():
    response = client.post(
        "/clients/",
        json={
            "nom": "Jean Dupont",
            "email": "jean.dupont@example.com",
            "adresse": "123 Rue de Paris",
            "type_client": "particulier"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "Jean Dupont"
    assert data["type_client"] == "particulier"
    assert "id" in data

def test_create_client_entreprise_valid():
    response = client.post(
        "/clients/",
        json={
            "nom": "Entreprise ABC",
            "email": "contact@abc.com",
            "adresse": "456 Avenue des Champs-Élysées",
            "siat_siren": "123456789",
            "tva_intracommunautaire": "FR123456789",
            "type_client": "entreprise"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "Entreprise ABC"
    assert data["siat_siren"] == "123456789"
    assert data["tva_intracommunautaire"] == "FR123456789"

def test_create_client_entreprise_missing_siren():
    response = client.post(
        "/clients/",
        json={
            "nom": "Entreprise ABC",
            "email": "contact@abc.com",
            "adresse": "456 Avenue des Champs-Élysées",
            "tva_intracommunautaire": "FR123456789",
            "type_client": "entreprise"
        }
    )
    assert response.status_code == 422 # Pydantic validation error

def test_create_client_entreprise_missing_tva():
    response = client.post(
        "/clients/",
        json={
            "nom": "Entreprise ABC",
            "email": "contact@abc.com",
            "adresse": "456 Avenue des Champs-Élysées",
            "siat_siren": "123456789",
            "type_client": "entreprise"
        }
    )
    assert response.status_code == 422 # Pydantic validation error

def test_get_clients():
    # Create a client first
    client.post("/clients/", json={"nom": "Client 1", "type_client": "particulier"})
    client.post("/clients/", json={"nom": "Client 2", "type_client": "particulier"})
    
    response = client.get("/clients/")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_get_client_by_id():
    response = client.post("/clients/", json={"nom": "Client 1", "type_client": "particulier"})
    client_id = response.json()["id"]
    
    response = client.get(f"/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["nom"] == "Client 1"

def test_get_client_not_found():
    response = client.get("/clients/999")
    assert response.status_code == 404

def test_update_client():
    response = client.post("/clients/", json={"nom": "Client 1", "type_client": "particulier"})
    client_id = response.json()["id"]
    
    response = client.put(
        f"/clients/{client_id}",
        json={"nom": "Client 1 Updated"}
    )
    assert response.status_code == 200
    assert response.json()["nom"] == "Client 1 Updated"

def test_update_client_to_entreprise_invalid():
    # Start as particulier
    response = client.post("/clients/", json={"nom": "Client 1", "type_client": "particulier"})
    client_id = response.json()["id"]
    
    # Try to update to entreprise without SIREN/TVA
    response = client.put(
        f"/clients/{client_id}",
        json={"type_client": "entreprise"}
    )
    assert response.status_code == 400 # Validation error from our custom check

def test_delete_client():
    response = client.post("/clients/", json={"nom": "Client 1", "type_client": "particulier"})
    client_id = response.json()["id"]
    
    response = client.delete(f"/clients/{client_id}")
    assert response.status_code == 204
    
    response = client.get(f"/clients/{client_id}")
    assert response.status_code == 404
