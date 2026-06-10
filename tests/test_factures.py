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

def test_facture_calculations():
    # Setup
    client_data = {"nom": "Calc Client", "type_client": "particulier"}
    client_resp = client.post("/clients/", json=client_data)
    client_id = client_resp.json()["id"]

    facture_data = {
        "numero": "FAC-CALC-001",
        "client_id": client_id,
        "date_facture": "2023-10-27",
        "lignes": [
            {"description": "Item 1", "quantite": 2, "prix_unitaire_ht": 100.0, "taux_tva": 20.0},
            {"description": "Item 2", "quantite": 1, "prix_unitaire_ht": 50.0, "taux_tva": 10.0}
        ]
    }
    response = client.post("/factures/", json=facture_data)
    assert response.status_code == 200 or response.status_code == 201
    data = response.json()

    # Item 1: 2 * 100 = 200 HT, 200 * 0.2 = 40 TVA, 240 TTC
    # Item 2: 1 * 50 = 50 HT, 50 * 0.1 = 5 TVA, 55 TTC
    # Totals: 250 HT, 45 TVA, 295 TTC

    for ligne in data["lignes"]:
        if ligne["description"] == "Item 1":
            assert ligne["montant_ht"] == 200.0
            assert ligne["montant_tva"] == 40.0
            assert ligne["montant_ttc"] == 240.0
        elif ligne["description"] == "Item 2":
            assert ligne["montant_ht"] == 50.0
            assert ligne["montant_tva"] == 5.0
            assert ligne["montant_ttc"] == 55.0

    assert data["total_ht"] == 250.0
    assert data["total_tva"] == 45.0
    assert data["total_ttc"] == 295.0


def test_read_factures_filtering():
    # Setup: Create two clients and several invoices
    c1_data = {"nom": "Filter Client 1", "type_client": "particulier"}
    c1_resp = client.post("/clients/", json=c1_data)
    c1_id = c1_resp.json()["id"]
    
    c2_data = {"nom": "Filter Client 2", "type_client": "particulier"}
    c2_resp = client.post("/clients/", json=c2_data)
    c2_id = c2_resp.json()["id"]
    
    # Invoices for Client 1
    f1_data = {"numero": "F-C1-D1", "client_id": c1_id, "date_facture": "2023-01-01", "lignes": []}
    f2_data = {"numero": "F-C1-D2", "client_id": c1_id, "date_facture": "2023-06-01", "lignes": []}
    client.post("/factures/", json=f1_data)
    client.post("/factures/", json=f2_data)
    
    # Invoices for Client 2
    f3_data = {"numero": "F-C2-D1", "client_id": c2_id, "date_facture": "2023-01-01", "lignes": []}
    f4_data = {"numero": "F-C2-D2", "client_id": c2_id, "date_facture": "2023-12-01", "lignes": []}
    client.post("/factures/", json=f3_data)
    client.post("/factures/", json=f4_data)
    
    # Test filter by client_id
    response = client.get(f"/factures/?client_id={c1_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(f["client_id"] == c1_id for f in data)
    
    # Test filter by date_start
    response = client.get("/factures/?date_start=2023-06-01")
    assert response.status_code == 200
    data = response.json()
    # Should have F-C1-D2 (2023-06-01) and F-C2-D2 (2023-12-01)
    assert len(data) == 2
    assert all(f["date_facture"] >= "2023-06-01" for f in data)
    
    # Test filter by date_end
    response = client.get("/factures/?date_end=2023-01-01")
    assert response.status_code == 200
    data = response.json()
    # Should have F-C1-D1 and F-C2-D1
    assert len(data) == 2
    assert all(f["date_facture"] <= "2023-01-01" for f in data)
    
    # Test filter by client and date
    response = client.get(f"/factures/?client_id={c1_id}&date_start=2023-06-01")
    assert response.status_code == 200
    data = response.json()
    # Should only have F-C1-D2
    assert len(data) == 1
    assert data[0]["numero"] == "F-C1-D2"

