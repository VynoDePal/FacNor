import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.services.numbering import get_next_sequence_value
from app.models import Sequence, Invoice, User, Client

# Setup an in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_sequential_numbering(db):
    # Test first number
    num1 = get_next_sequence_value(db, "invoice_seq", "F-")
    assert num1 == "F-001"
    
    # Test second number
    num2 = get_next_sequence_value(db, "invoice_seq", "F-")
    assert num2 == "F-002"
    
    # Test third number
    num3 = get_next_sequence_value(db, "invoice_seq", "F-")
    assert num3 == "F-003"

def test_multiple_sequences(db):
    # Test invoice sequence
    num_inv1 = get_next_sequence_value(db, "invoice_seq", "F-")
    assert num_inv1 == "F-001"
    
    # Test another sequence (e.g., quotes/devis)
    num_quote1 = get_next_sequence_value(db, "quote_seq", "D-")
    assert num_quote1 == "D-001"
    
    # Increment invoice again
    num_inv2 = get_next_sequence_value(db, "invoice_seq", "F-")
    assert num_inv2 == "F-002"

def test_persistence(db):
    # Generate some numbers
    get_next_sequence_value(db, "invoice_seq", "F-")
    get_next_sequence_value(db, "invoice_seq", "F-")
    
    # Check if the sequence value is persisted in the DB
    seq = db.query(Sequence).filter(Sequence.name == "invoice_seq").first()
    assert seq is not None
    assert seq.current_value == 2

def test_invoice_creation_numbering(db):
    # We need a user and a client for the Invoice model constraints
    user = User(username="testuser", email="test@example.com", hashed_password="password")
    client = Client(name="Test Client", email="client@example.com")
    db.add_all([user, client])
    db.commit()
    
    # Manually simulate the logic in the API endpoint
    invoice_number = get_next_sequence_value(db, "invoice_seq", "F-")
    new_invoice = Invoice(
        invoice_number=invoice_number,
        date=datetime.datetime.now(),
        client_id=client.id,
        user_id=user.id,
        total_ht=0,
        total_tva=0,
        total_ttc=0
    )
    db.add(new_invoice)
    db.commit()
    
    assert new_invoice.invoice_number == "F-001"
    
    # Create another one
    invoice_number2 = get_next_sequence_value(db, "invoice_seq", "F-")
    new_invoice2 = Invoice(
        invoice_number=invoice_number2,
        date=datetime.datetime.now(),
        client_id=client.id,
        user_id=user.id,
        total_ht=0,
        total_tva=0,
        total_ttc=0
    )
    db.add(new_invoice2)
    db.commit()
    
    assert new_invoice2.invoice_number == "F-002"
