import pytest
from app.models.user import User
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from sqlalchemy.exc import IntegrityError
from datetime import date

def test_create_user(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="hashed_password")
    db_session.add(user)
    db_session.commit()
    
    db_user = db_session.query(User).filter(User.username == "testuser").first()
    assert db_user is not None
    assert db_user.email == "test@example.com"

def test_create_client(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="hashed_password")
    db_session.add(user)
    db_session.commit()
    
    client = Client(
        user_id=user.id,
        name="Test Client Ltd",
        email="client@example.com",
        is_company=True,
        siren="123456789",
        vat_number="FR123456789"
    )
    db_session.add(client)
    db_session.commit()
    
    db_client = db_session.query(Client).filter(Client.name == "Test Client Ltd").first()
    assert db_client is not None
    assert db_client.user_id == user.id
    assert db_client.siren == "123456789"

def test_create_invoice(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="hashed_password")
    db_session.add(user)
    db_session.commit()
    
    client = Client(user_id=user.id, name="Test Client")
    db_session.add(client)
    db_session.commit()
    
    invoice = Invoice(
        user_id=user.id,
        client_id=client.id,
        invoice_number="INV-2023-001",
        date=date(2023, 1, 1),
        status="draft"
    )
    db_session.add(invoice)
    db_session.commit()
    
    db_invoice = db_session.query(Invoice).filter(Invoice.invoice_number == "INV-2023-001").first()
    assert db_invoice is not None
    assert db_invoice.client_id == client.id

def test_create_invoice_items(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="hashed_password")
    db_session.add(user)
    db_session.commit()
    
    client = Client(user_id=user.id, name="Test Client")
    db_session.add(client)
    db_session.commit()
    
    invoice = Invoice(
        user_id=user.id,
        client_id=client.id,
        invoice_number="INV-2023-001",
        date=date(2023, 1, 1)
    )
    db_session.add(invoice)
    db_session.commit()
    
    item1 = InvoiceItem(
        invoice_id=invoice.id,
        description="Service A",
        quantity=1.0,
        unit_price_ht=100.0,
        vat_rate=20.0
    )
    item2 = InvoiceItem(
        invoice_id=invoice.id,
        description="Service B",
        quantity=2.0,
        unit_price_ht=50.0,
        vat_rate=20.0
    )
    db_session.add_all([item1, item2])
    db_session.commit()
    
    items = db_session.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).all()
    assert len(items) == 2
    assert items[0].description == "Service A" or items[1].description == "Service A"

def test_invoice_number_uniqueness_per_user(db_session):
    user1 = User(username="user1", email="u1@example.com", hashed_password="pw")
    user2 = User(username="user2", email="u2@example.com", hashed_password="pw")
    db_session.add_all([user1, user2])
    db_session.commit()
    
    client = Client(user_id=user1.id, name="Client 1")
    db_session.add(client)
    db_session.commit()
    
    invoice1 = Invoice(
        user_id=user1.id,
        client_id=client.id,
        invoice_number="INV-001",
        date=date(2023, 1, 1)
    )
    db_session.add(invoice1)
    db_session.commit()
    
    # This should fail because user1 already has INV-001
    invoice2 = Invoice(
        user_id=user1.id,
        client_id=client.id,
        invoice_number="INV-001",
        date=date(2023, 1, 2)
    )
    db_session.add(invoice2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    
    db_session.rollback()
    
    # This should succeed because it's a different user
    invoice3 = Invoice(
        user_id=user2.id,
        client_id=client.id, # technically should be user2's client, but for test we use client 1
        invoice_number="INV-001",
        date=date(2023, 1, 2)
    )
    # We need a client for user2
    client2 = Client(user_id=user2.id, name="Client 2")
    db_session.add(client2)
    db_session.commit()
    
    invoice3 = Invoice(
        user_id=user2.id,
        client_id=client2.id,
        invoice_number="INV-001",
        date=date(2023, 1, 2)
    )
    db_session.add(invoice3)
    db_session.commit()
    
    db_invoice3 = db_session.query(Invoice).filter(Invoice.invoice_number == "INV-001", Invoice.user_id == user2.id).first()
    assert db_invoice3 is not None
