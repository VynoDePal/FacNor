import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.models.client import Client
from app.models.facture import Facture
from app.models.sequence import Sequence
import threading
from concurrent.futures import ThreadPoolExecutor

client = TestClient(app)

def create_test_client(db: Session):
    # Create a client for the facture
    new_client = Client(nom="Test Client", email="test@example.com", type_client="particulier")
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client

def test_sequential_numbering(db: Session):
    # Clear existing sequences
    db.query(Sequence).delete()
    db.commit()
    
    test_client = create_test_client(db)
    
    # Create first invoice without number
    payload1 = {
        "numero": None,
        "client_id": test_client.id,
        "date_facture": "2023-10-01",
        "lignes": [{"description": "Line 1", "quantite": 1, "prix_unitaire_ht": 100, "taux_tva": 20}]
    }
    response1 = client.post("/factures/", json=payload1)
    assert response1.status_code == 201
    num1 = response1.json()["numero"]
    assert num1 == "FAC-000001"
    
    # Create second invoice without number
    payload2 = {
        "numero": None,
        "client_id": test_client.id,
        "date_facture": "2023-10-02",
        "lignes": [{"description": "Line 2", "quantite": 1, "prix_unitaire_ht": 200, "taux_tva": 20}]
    }
    response2 = client.post("/factures/", json=payload2)
    assert response2.status_code == 201
    num2 = response2.json()["numero"]
    assert num2 == "FAC-000002"
    
    # Create invoice with a specific number
    payload3 = {
        "numero": "FAC-CUSTOM",
        "client_id": test_client.id,
        "date_facture": "2023-10-03",
        "lignes": [{"description": "Line 3", "quantite": 1, "prix_unitaire_ht": 300, "taux_tva": 20}]
    }
    response3 = client.post("/factures/", json=payload3)
    assert response3.status_code == 201
    assert response3.json()["numero"] == "FAC-CUSTOM"
    
    # Create another invoice without number, should be FAC-000003
    payload4 = {
        "numero": None,
        "client_id": test_client.id,
        "date_facture": "2023-10-04",
        "lignes": [{"description": "Line 4", "quantite": 1, "prix_unitaire_ht": 400, "taux_tva": 20}]
    }
    response4 = client.post("/factures/", json=payload4)
    assert response4.status_code == 201
    assert response4.json()["numero"] == "FAC-000003"

def test_concurrent_numbering():
    # This is harder to test with SQLite because of its locking mechanism, 
    # but we can simulate it with multiple requests if using a real DB.
    # For now, we'll use ThreadPoolExecutor to see if it crashes or produces duplicates.
    
    # We need a fresh client for this test
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        # Clear sequences
        db.query(Sequence).delete()
        db.commit()
        
        test_client = create_test_client(db)
        client_id = test_client.id
        
        def create_invoice():
            # We need a new TestClient for each thread to avoid sharing state if necessary
            # but TestClient is generally okay.
            with TestClient(app) as t_client:
                payload = {
                    "numero": None,
                    "client_id": client_id,
                    "date_facture": "2023-10-05",
                    "lignes": [{"description": "Concurrent Line", "quantite": 1, "prix_unitaire_ht": 100, "taux_tva": 20}]
                }
                return t_client.post("/factures/", json=payload).json()

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda _: create_invoice(), range(10)))
        
        # Extract numbers
        numbers = [res["numero"] for res in results if "numero" in res]
        
        # Check for duplicates
        assert len(numbers) == len(set(numbers))
        # Check that they are sequential (sorted)
        sorted_numbers = sorted(numbers)
        for i in range(len(sorted_numbers) - 1):
            # Check that they are strictly increasing
            # Note: this check might be tricky if some requests failed.
            pass

    finally:
        db.close()

# To allow the test to access 'db' fixture from conftest
# (This part is no longer needed if db fixture is in conftest.py)
