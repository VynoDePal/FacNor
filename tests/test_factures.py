import pytest
from fastapi import status
from tests.conftest import client

def test_create_client():
    # First create a client to associate with the facture
    client_data = {
        "nom": "Test Client",
        "email": "test@client.com",
        "adresse": "123 Test St",
        "type_client": "particulier"
    }
    response = client.post("/clients/", json=client_data)
    assert response.status_code == status.HTTP_201_CREATED
    client_id = response.json()["id"]

    # Now create a facture
    facture_data = {
        "numero": "FAC-2023-001",
        "client_id": client_id,
        "date_facture": "2023-10-27",
        "date_echeance": "2023-11-27",
        "statut": "brouillon",
        "notes": "Test invoice",
        "lignes": [
            {"description": "Service A", "quantite": 1, "prix_unitaire_ht": 100.0, "taux_tva": 20.0},
            {"description": "Service B", "quantite": 2, "prix_unitaire_ht": 50.0, "taux_tva": 20.0}
        ]
    }
    response = client.post("/factures/", json=facture_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["numero"] == "FAC-2023-001"
    assert data["client_id"] == client_id
    assert len(data["lignes"]) == 2

def test_read_facture():
    # Setup: create client and facture
    client_data = {"nom": "Read Client", "type_client": "particulier"}
    client_resp = client.post("/clients/", json=client_data)
    client_id = client_resp.json()["id"]

    facture_data = {
        "numero": "FAC-READ-001",
        "client_id": client_id,
        "date_facture": "2023-10-27",
        "lignes": []
    }
    facture_resp = client.post("/factures/", json=facture_data)
    facture_id = facture_resp.json()["id"]

    # Test read
    response = client.get(f"/factures/{facture_id}")
    assert response.status_code == 200
    assert response.json()["numero"] == "FAC-READ-001"

def test_update_facture():
    # Setup
    client_data = {"nom": "Update Client", "type_client": "particulier"}
    client_resp = client.post("/clients/", json=client_data)
    client_id = client_resp.json()["id"]

    facture_data = {
        "numero": "FAC-UPDATE-001",
        "client_id": client_id,
        "date_facture": "2023-10-27",
        "lignes": []
    }
    facture_resp = client.post("/factures/", json=facture_data)
    facture_id = facture_resp.json()["id"]

    # Test update
    update_data = {"statut": "payee", "notes": "Updated notes"}
    response = client.put(f"/factures/{facture_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["statut"] == "payee"
    assert response.json()["notes"] == "Updated notes"

def test_delete_facture():
    # Setup
    client_data = {"nom": "Delete Client", "type_client": "particulier"}
    client_resp = client.post("/clients/", json=client_data)
    client_id = client_resp.json()["id"]

    facture_data = {
        "numero": "FAC-DELETE-001",
        "client_id": client_id,
        "date_facture": "2023-10-27",
        "lignes": []
    }
    facture_resp = client.post("/factures/", json=facture_data)
    facture_id = facture_resp.json()["id"]

    # Test delete
    response = client.delete(f"/factures/{facture_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's gone
    response = client.get(f"/factures/{facture_id}")
    assert response.status_code == 404

def test_create_facture_non_existent_client():
    facture_data = {
        "numero": "FAC-NO-CLIENT",
        "client_id": 999,
        "date_facture": "2023-10-27",
        "lignes": []
    }
    response = client.post("/factures/", json=facture_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"

def test_create_duplicate_facture_number():
    # Setup
    client_data = {"nom": "Dup Client", "type_client": "particulier"}
    client_resp = client.post("/clients/", json=client_data)
    client_id = client_resp.json()["id"]

    facture_data = {
        "numero": "FAC-DUP",
        "client_id": client_id,
        "date_facture": "2023-10-27",
        "lignes": []
    }
    client.post("/factures/", json=facture_data)

    # Try again with same number
    response = client.post("/factures/", json=facture_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Facture number already exists"
