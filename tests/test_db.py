from app.core.database import Base, engine
from app.models import models
import pytest
from sqlalchemy.orm import sessionmaker

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    # Create tables for the test database
    Base.metadata.create_all(bind=engine)
    connection = TestSessionLocal()
    try:
        yield connection
    finally:
        connection.close()
        Base.metadata.drop_all(bind=engine)

def test_database_tables_created(db):
    # Verify that tables exist in the database
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    assert "users" in tables
    assert "clients" in tables
    assert "invoices" in tables
    assert "invoice_lines" in tables

def test_client_creation(db):
    client = models.Client(name="Test Client", email="test@client.com")
    db.add(client)
    db.commit()
    db.refresh(client)
    assert client.id is not None
    assert client.name == "Test Client"

def test_invoice_creation(db):
    client = models.Client(name="Test Client")
    db.add(client)
    db.commit()
    
    invoice = models.Invoice(invoice_number="INV-2023-001", client_id=client.id)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    assert invoice.id is not None
    assert invoice.invoice_number == "INV-2023-001"
    assert invoice.client_id == client.id
