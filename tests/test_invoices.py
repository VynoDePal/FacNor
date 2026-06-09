import pytest
from app.core.database import get_db

def test_create_invoice(client, db):
    # Create a client first
    client_resp = client.post(
        "/clients/",
        json={"name": "Invoice Client", "email": "invoice@example.com", "address": "123 Inv St", "vat_number": "FR111", "siren": "111"}
    )
    client_id = client_resp.json()["id"]
    
    # Create invoice
    invoice_data = {
        "invoice_number": "INV-2023-001",
        "client_id": client_id,
        "issue_date": "2023-10-01T10:00:00",
        "due_date": "2023-10-31T10:00:00",
        "status": "draft",
        "lines": [
            {"description": "Product 1", "quantity": 2, "unit_price_ht": 50.0, "tva_rate": 20.0, "total_ht": 100.0},
            {"description": "Product 2", "quantity": 1, "unit_price_ht": 20.0, "tva_rate": 20.0, "total_ht": 20.0}
        ]
    }
    response = client.post("/invoices/", json=invoice_data)
    assert response.status_code == 201
    data = response.json()
    assert data["invoice_number"] == "INV-2023-001"
    assert data["client_id"] == client_id
    assert len(data["lines"]) == 2
    # Totals should be recalculated: 100 + 20 = 120 HT, TVA = 120 * 0.2 = 24, TTC = 144
    assert float(data["total_ht"]) == 120.0
    assert float(data["total_tva"]) == 24.0
    assert float(data["total_ttc"]) == 144.0

def test_create_invoice_client_not_found(client):
    invoice_data = {
        "invoice_number": "INV-ERR",
        "client_id": 999,
        "lines": []
    }
    response = client.post("/invoices/", json=invoice_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"

def test_read_invoices(client, db):
    # Create client and invoice
    client_resp = client.post("/clients/", json={"name": "List Client", "siren": "123"})
    client_id = client_resp.json()["id"]
    
    client.post("/invoices/", json={
        "invoice_number": "INV-LIST-1",
        "client_id": client_id,
        "lines": [{"description": "L1", "quantity": 1, "unit_price_ht": 10.0, "tva_rate": 20.0, "total_ht": 10.0}]
    })
    
    # Read all
    response = client.get("/invoices/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # Filter by client
    response = client.get(f"/invoices/?client_id={client_id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["client_id"] == client_id

def test_read_invoice_by_id(client, db):
    client_resp = client.post("/clients/", json={"name": "Read Client", "siren": "123"})
    client_id = client_resp.json()["id"]
    
    inv_resp = client.post("/invoices/", json={
        "invoice_number": "INV-READ",
        "client_id": client_id,
        "lines": []
    })
    invoice_id = inv_resp.json()["id"]
    
    response = client.get(f"/invoices/{invoice_id}")
    assert response.status_code == 200
    assert response.json()["invoice_number"] == "INV-READ"

def test_read_invoice_not_found(client):
    response = client.get("/invoices/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Invoice not found"

def test_update_invoice(client, db):
    client_resp = client.post("/clients/", json={"name": "Update Client", "siren": "123"})
    client_id = client_resp.json()["id"]
    
    inv_resp = client.post("/invoices/", json={
        "invoice_number": "INV-UPDATE",
        "client_id": client_id,
        "lines": []
    })
    invoice_id = inv_resp.json()["id"]
    
    response = client.put(f"/invoices/{invoice_id}", json={"status": "paid", "invoice_number": "INV-UPDATED"})
    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert response.json()["invoice_number"] == "INV-UPDATED"

def test_delete_invoice(client, db):
    client_resp = client.post("/clients/", json={"name": "Delete Client", "siren": "123"})
    client_id = client_resp.json()["id"]
    
    inv_resp = client.post("/invoices/", json={
        "invoice_number": "INV-DELETE",
        "client_id": client_id,
        "lines": []
    })
    invoice_id = inv_resp.json()["id"]
    
    response = client.delete(f"/invoices/{invoice_id}")
    assert response.status_code == 204
    
    response = client.get(f"/invoices/{invoice_id}")
    assert response.status_code == 404

def test_automatic_invoice_numbering(client, db):
    # Create a client
    client_resp = client.post(
        "/clients/",
        json={"name": "Auto Num Client", "email": "auto@example.com", "address": "123 Auto St", "vat_number": "FR222", "siren": "222"}
    )
    client_id = client_resp.json()["id"]

    # Create first invoice without number
    inv1_data = {
        "client_id": client_id,
        "lines": [{"description": "L1", "quantity": 1, "unit_price_ht": 10.0, "tva_rate": 20.0, "total_ht": 10.0}]
    }
    resp1 = client.post("/invoices/", json=inv1_data)
    assert resp1.status_code == 201
    num1 = resp1.json()["invoice_number"]
    assert num1.startswith("FAC-")
    assert num1.endswith("000001")

    # Create second invoice without number
    inv2_data = {
        "client_id": client_id,
        "lines": [{"description": "L2", "quantity": 1, "unit_price_ht": 10.0, "tva_rate": 20.0, "total_ht": 10.0}]
    }
    resp2 = client.post("/invoices/", json=inv2_data)
    assert resp2.status_code == 201
    num2 = resp2.json()["invoice_number"]
    assert num2.startswith("FAC-")
    assert num2.endswith("000002")

    # Create third invoice with a specific number (should not affect sequence)
    inv3_data = {
        "invoice_number": "MANUAL-001",
        "client_id": client_id,
        "lines": [{"description": "L3", "quantity": 1, "unit_price_ht": 10.0, "tva_rate": 20.0, "total_ht": 10.0}]
    }
    resp3 = client.post("/invoices/", json=inv3_data)
    assert resp3.status_code == 201
    assert resp3.json()["invoice_number"] == "MANUAL-001"

    # Create fourth invoice without number (should follow the sequence)
    inv4_data = {
        "client_id": client_id,
        "lines": [{"description": "L4", "quantity": 1, "unit_price_ht": 10.0, "tva_rate": 20.0, "total_ht": 10.0}]
    }
    resp4 = client.post("/invoices/", json=inv4_data)
    assert resp4.status_code == 201
    num4 = resp4.json()["invoice_number"]
    assert num4.startswith("FAC-")
    assert num4.endswith("000003")


def test_read_invoices_filtering(client, db):
    # Setup: Create multiple clients and invoices
    c1_resp = client.post("/clients/", json={"name": "C1", "siren": "S1"})
    c1_id = c1_resp.json()["id"]
    c2_resp = client.post("/clients/", json={"name": "C2", "siren": "S2"})
    c2_id = c2_resp.json()["id"]

    # Invoice 1: Client 1, 2023-01-01, 100€ TTC (83.33 * 1.2 = 99.996)
    # To be precise, let's use unit_price_ht that gives round TTC
    client.post("/invoices/", json={
        "invoice_number": "FILT-1",
        "client_id": c1_id,
        "issue_date": "2023-01-01T10:00:00",
        "lines": [{"description": "L1", "quantity": 1, "unit_price_ht": 100.0, "tva_rate": 0.0, "total_ht": 100.0}]
    })
    # Invoice 2: Client 1, 2023-06-01, 200€ TTC
    client.post("/invoices/", json={
        "invoice_number": "FILT-2",
        "client_id": c1_id,
        "issue_date": "2023-06-01T10:00:00",
        "lines": [{"description": "L2", "quantity": 1, "unit_price_ht": 200.0, "tva_rate": 0.0, "total_ht": 200.0}]
    })
    # Invoice 3: Client 2, 2023-01-01, 300€ TTC
    client.post("/invoices/", json={
        "invoice_number": "FILT-3",
        "client_id": c2_id,
        "issue_date": "2023-01-01T10:00:00",
        "lines": [{"description": "L3", "quantity": 1, "unit_price_ht": 300.0, "tva_rate": 0.0, "total_ht": 300.0}]
    })

    # Test filter by client
    resp = client.get(f"/invoices/?client_id={c1_id}")
    assert len(resp.json()) == 2
    
    # Test filter by start_date
    resp = client.get("/invoices/?start_date=2023-05-01")
    assert len(resp.json()) == 1
    assert resp.json()[0]["invoice_number"] == "FILT-2"
    
    # Test filter by end_date
    resp = client.get("/invoices/?end_date=2023-02-01")
    assert len(resp.json()) == 2 # FILT-1 and FILT-3
    
    # Test filter by min_amount
    resp = client.get("/invoices/?min_amount=250")
    assert len(resp.json()) == 1
    assert resp.json()[0]["invoice_number"] == "FILT-3"
    
    # Test filter by max_amount
    resp = client.get("/invoices/?max_amount=150")
    assert len(resp.json()) == 1
    assert resp.json()[0]["invoice_number"] == "FILT-1"

    # Test combined filters
    resp = client.get(f"/invoices/?client_id={c1_id}&min_amount=150")
    assert len(resp.json()) == 1
    assert resp.json()[0]["invoice_number"] == "FILT-2"


def test_download_invoice_pdf(client, db):
    # Create a client and invoice
    client_resp = client.post("/clients/", json={"name": "PDF Client", "siren": "123"})
    client_id = client_resp.json()["id"]
    
    inv_resp = client.post("/invoices/", json={
        "invoice_number": "PDF-TEST",
        "client_id": client_id,
        "lines": [{"description": "L1", "quantity": 1, "unit_price_ht": 10.0, "tva_rate": 20.0, "total_ht": 10.0}]
    })
    invoice_id = inv_resp.json()["id"]
    
    # Download PDF
    response = client.get(f"/invoices/{invoice_id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.content) > 0

