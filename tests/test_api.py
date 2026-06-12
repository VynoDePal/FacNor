import pytest

def test_auth_register(client):
    response = client.post("/auth/register", json={
        "username": "reguser",
        "password": "regpassword",
        "email": "reg@example.com"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "reguser"

def test_auth_login(client):
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

def test_create_client(client, auth_header):
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

def test_create_invoice(client, auth_header):
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

def test_read_client(client, auth_header):
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "Client Read Test",
        "is_company": False
    }, headers=auth_header)
    client_id = client_resp.json()["id"]

    # Read client
    response = client.get(f"/clients/{client_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["name"] == "Client Read Test"

def test_read_client_not_found(client, auth_header):
    response = client.get("/clients/999", headers=auth_header)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"

def test_update_client(client, auth_header):
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "Client Update Test",
        "is_company": False
    }, headers=auth_header)
    client_id = client_resp.json()["id"]

    # Update client
    update_data = {
        "name": "Client Updated Name",
        "address": "New Address",
        "email": "updated@client.com",
        "phone": "0987654321",
        "siren": "987654321",
        "tva_number": "FR987654321",
        "is_company": True
    }
    response = client.put(f"/clients/{client_id}", json=update_data, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["name"] == "Client Updated Name"
    assert response.json()["is_company"] is True

    # Verify update
    read_resp = client.get(f"/clients/{client_id}", headers=auth_header)
    assert read_resp.json()["name"] == "Client Updated Name"

def test_update_client_not_found(client, auth_header):
    response = client.put("/clients/999", json={"name": "Non existent"}, headers=auth_header)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"

def test_delete_client(client, auth_header):
    # Create client
    client_resp = client.post("/clients/", json={
        "name": "Client Delete Test",
        "is_company": False
    }, headers=auth_header)
    client_id = client_resp.json()["id"]

    # Delete client
    response = client.delete(f"/clients/{client_id}", headers=auth_header)
    assert response.status_code == 204

    # Verify deletion
    read_resp = client.get(f"/clients/{client_id}", headers=auth_header)
    assert read_resp.status_code == 404

def test_delete_client_not_found(client, auth_header):
    response = client.delete("/clients/999", headers=auth_header)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"


def test_read_invoice(client, auth_header):
    # Create client
    client_resp = client.post("/clients/", json={"name": "Client Read Invoice", "is_company": False}, headers=auth_header)
    client_id = client_resp.json()["id"]

    # Create invoice
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header)
    invoice_id = invoice_resp.json()["id"]

    # Read invoice
    response = client.get(f"/invoices/{invoice_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["client_id"] == client_id

def test_update_invoice(client, auth_header):
    # Create client
    client_resp = client.post("/clients/", json={"name": "Client Update Invoice", "is_company": False}, headers=auth_header)
    client_id = client_resp.json()["id"]

    # Create invoice
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header)
    invoice_id = invoice_resp.json()["id"]

    # Update invoice
    update_data = {
        "client_id": client_id,
        "date_issued": "2023-10-02",
        "status": "sent",
        "notes": "Updated notes",
        "lines": [{"description": "Item 1 Updated", "quantity": 2.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }
    response = client.put(f"/invoices/{invoice_id}", json=update_data, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["date_issued"] == "2023-10-02"
    assert response.json()["status"] == "sent"
    assert response.json()["notes"] == "Updated notes"
    assert len(response.json()["lines"]) == 1
    assert response.json()["lines"][0]["description"] == "Item 1 Updated"
    assert response.json()["lines"][0]["quantity"] == 2.0

def test_delete_invoice(client, auth_header):
    # Create client
    client_resp = client.post("/clients/", json={"name": "Client Delete Invoice", "is_company": False}, headers=auth_header)
    client_id = client_resp.json()["id"]

    # Create invoice
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header)
    invoice_id = invoice_resp.json()["id"]

    # Delete invoice
    response = client.delete(f"/invoices/{invoice_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["detail"] == "Invoice deleted successfully"

    # Verify deletion
    read_resp = client.get(f"/invoices/{invoice_id}", headers=auth_header)
    assert read_resp.status_code == 404

def test_invoice_access_control(client):
    # User 1
    client.post("/auth/register", json={"username": "user1", "password": "pass1", "email": "user1@example.com"})
    response1 = client.post("/auth/login", data={"username": "user1", "password": "pass1"})
    auth_header1 = {"Authorization": f"Bearer {response1.json()['access_token']}"}

    # User 2
    client.post("/auth/register", json={"username": "user2", "password": "pass2", "email": "user2@example.com"})
    response2 = client.post("/auth/login", data={"username": "user2", "password": "pass2"})
    auth_header2 = {"Authorization": f"Bearer {response2.json()['access_token']}"}

    # User 1 creates a client and invoice
    client_resp = client.post("/clients/", json={"name": "User1 Client", "is_company": False}, headers=auth_header1)
    client_id = client_resp.json()["id"]
    invoice_resp = client.post("/invoices/", json={
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }, headers=auth_header1)
    invoice_id = invoice_resp.json()["id"]

    # User 2 tries to read User 1's invoice
    response = client.get(f"/invoices/{invoice_id}", headers=auth_header2)
    assert response.status_code == 403

    # User 2 tries to update User 1's invoice
    update_data = {
        "client_id": client_id,
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 0.20}]
    }
    response = client.put(f"/invoices/{invoice_id}", json=update_data, headers=auth_header2)
    assert response.status_code == 403

    # User 2 tries to delete User 1's invoice
    response = client.delete(f"/invoices/{invoice_id}", headers=auth_header2)
    assert response.status_code == 403

def test_search_invoices(client, auth_header):
    # Create clients
    c1 = client.post("/clients/", json={"name": "Client Alpha", "is_company": False}, headers=auth_header).json()
    c2 = client.post("/clients/", json={"name": "Client Beta", "is_company": False}, headers=auth_header).json()

    # Create invoices
    i1 = client.post("/invoices/", json={
        "invoice_number": "INV-001",
        "client_id": c1["id"],
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 1", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 20.0}]
    }, headers=auth_header).json()
    
    i2 = client.post("/invoices/", json={
        "invoice_number": "INV-002",
        "client_id": c2["id"],
        "date_issued": "2023-10-01",
        "lines": [{"description": "Item 2", "quantity": 1.0, "unit_price_ht": 100.0, "vat_rate": 20.0}]
    }, headers=auth_header).json()

    # Search by invoice number
    resp = client.get("/invoices/?q=INV-001", headers=auth_header)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["invoice_number"] == "INV-001"

    # Search by client name
    resp = client.get("/invoices/?q=Alpha", headers=auth_header)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["invoice_number"] == "INV-001"

    # Search by something that matches both or neither
    resp = client.get("/invoices/?q=nonexistent", headers=auth_header)
    assert resp.status_code == 200
    assert len(resp.json()) == 0

