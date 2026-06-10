import pytest
from fastapi.testclient import TestClient
from app.main import app
import sqlite3
import os

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Ensure a clean database for tests
    db_file = "facnor.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    
    # Run the schema.sql to create tables
    schema_path = "schema.sql"
    with sqlite3.connect(db_file) as conn:
        with open(schema_path, "r") as f:
            conn.executescript(f.read())
        conn.commit()
    
    yield
    # Clean up after tests if necessary
    # if os.path.exists(db_file):
    #     os.remove(db_file)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FacNor API", "status": "ok"}

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_database_tables_exist():
    db_file = "facnor.db"
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        # Check for clients table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
        assert cursor.fetchone() is not None
        # Check for factures table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='factures'")
        assert cursor.fetchone() is not None
        # Check for lignes_facture table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lignes_facture'")
        assert cursor.fetchone() is not None
