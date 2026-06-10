import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Client, Invoice, InvoiceLine

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_create_user(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="password123")
    db_session.add(user)
    db_session.commit()
    
    retrieved_user = db_session.query(User).filter_by(username="testuser").first()
    assert retrieved_user is not None
    assert retrieved_user.email == "test@example.com"

def test_create_client_b2b(db_session):
    client = Client(
        name="Company ABC", 
        email="contact@abc.com", 
        address="123 Business St, Paris", 
        vat_number="FR123456789", 
        is_business=True
    )
    db_session.add(client)
    db_session.commit()
    
    retrieved_client = db_session.query(Client).filter_by(name="Company ABC").first()
    assert retrieved_client is not None
    assert retrieved_client.is_business is True
    assert retrieved_client.vat_number == "FR123456789"

def test_create_client_b2c(db_session):
    client = Client(
        name="Jean Dupont", 
        email="jean@example.com", 
        address="456 Home Ave, Lyon", 
        is_business=False
    )
    db_session.add(client)
    db_session.commit()
    
    retrieved_client = db_session.query(Client).filter_by(name="Jean Dupont").first()
    assert retrieved_client is not None
    assert retrieved_client.is_business is False
    assert retrieved_client.vat_number is None

def test_invoice_relationship(db_session):
    user = User(username="admin", email="admin@example.com", hashed_password="password")
    client = Client(name="Client XYZ", is_business=False)
    db_session.add_all([user, client])
    db_session.commit()
    
    invoice = Invoice(
        invoice_number="INV-2023-001",
        date=datetime.utcnow(),
        client_id=client.id,
        user_id=user.id,
        total_ht=100.0,
        total_tva=20.0,
        total_ttc=120.0
    )
    db_session.add(invoice)
    db_session.commit()
    
    assert invoice.id is not None
    assert invoice.client.name == "Client XYZ"
    assert invoice.user.username == "admin"

def test_invoice_lines_relationship(db_session):
    user = User(username="admin", email="admin@example.com", hashed_password="password")
    client = Client(name="Client XYZ", is_business=False)
    db_session.add_all([user, client])
    db_session.commit()
    
    invoice = Invoice(
        invoice_number="INV-2023-002",
        date=datetime.utcnow(),
        client_id=client.id,
        user_id=user.id,
        total_ht=200.0,
        total_tva=40.0,
        total_ttc=240.0
    )
    db_session.add(invoice)
    db_session.commit()
    
    line1 = InvoiceLine(
        invoice_id=invoice.id,
        description="Service A",
        quantity=1.0,
        unit_price=100.0,
        tax_rate=20.0,
        total_ht=100.0,
        total_tva=20.0,
        total_ttc=120.0
    )
    line2 = InvoiceLine(
        invoice_id=invoice.id,
        description="Service B",
        quantity=2.0,
        unit_price=50.0,
        tax_rate=20.0,
        total_ht=100.0,
        total_tva=20.0,
        total_ttc=120.0
    )
    db_session.add_all([line1, line2])
    db_session.commit()
    
    assert len(invoice.lines) == 2
    assert invoice.lines[0].description in ["Service A", "Service B"]

def test_invoice_deletion_cascade(db_session):
    user = User(username="admin", email="admin@example.com", hashed_password="password")
    client = Client(name="Client XYZ", is_business=False)
    db_session.add_all([user, client])
    db_session.commit()
    
    invoice = Invoice(
        invoice_number="INV-2023-003",
        date=datetime.utcnow(),
        client_id=client.id,
        user_id=user.id,
        total_ht=100.0,
        total_tva=20.0,
        total_ttc=120.0
    )
    db_session.add(invoice)
    db_session.commit()
    
    line = InvoiceLine(
        invoice_id=invoice.id,
        description="Item",
        quantity=1.0,
        unit_price=100.0,
        tax_rate=20.0,
        total_ht=100.0,
        total_tva=20.0,
        total_ttc=120.0
    )
    db_session.add(line)
    db_session.commit()
    
    invoice_id = invoice.id
    db_session.delete(invoice)
    db_session.commit()
    
    assert db_session.query(Invoice).filter_by(id=invoice_id).first() is None
    assert db_session.query(InvoiceLine).filter_by(invoice_id=invoice_id).first() is None
