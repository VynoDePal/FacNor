import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.models import Invoice, InvoiceLine, Client, User
from app.core.tax_engine import calculate_invoice_totals, calculate_line_total

# Database setup for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_calculate_line_total():
    # Mock InvoiceLine
    class MockLine:
        def __init__(self, quantity, unit_price_ht, vat_rate):
            self.quantity = quantity
            self.unit_price_ht = unit_price_ht
            self.vat_rate = vat_rate

    line = MockLine(2, 100.0, 0.20) # 2 * 100 * 1.2 = 240
    assert calculate_line_total(line) == 240.0

def test_calculate_invoice_totals():
    # Mock InvoiceLine
    class MockLine:
        def __init__(self, quantity, unit_price_ht, vat_rate):
            self.quantity = quantity
            self.unit_price_ht = unit_price_ht
            self.vat_rate = vat_rate

    lines = [
        MockLine(1, 100.0, 0.20), # HT=100, VAT=20, TTC=120
        MockLine(2, 50.0, 0.10),  # HT=100, VAT=10, TTC=110
    ]
    
    totals = calculate_invoice_totals(lines)
    assert totals["total_ht"] == 200.0
    assert totals["total_vat"] == 30.0
    assert totals["total_ttc"] == 230.0

def test_invoice_model_properties(db):
    # Setup data
    user = User(username="testuser", email="test@example.com", password_hash="hash")
    client = Client(name="Test Client")
    db.add(user)
    db.add(client)
    db.commit()

    from datetime import date
    invoice = Invoice(
        invoice_number="INV-001",
        client_id=client.id,
        user_id=user.id,
        date_issued=date(2023, 1, 1)
    )
    db.add(invoice)
    db.commit()

    lines = [
        InvoiceLine(description="Item 1", quantity=1, unit_price_ht=100.0, vat_rate=0.20, invoice_id=invoice.id),
        InvoiceLine(description="Item 2", quantity=2, unit_price_ht=50.0, vat_rate=0.10, invoice_id=invoice.id),
    ]
    db.add_all(lines)
    db.commit()

    # Test properties
    assert invoice.total_ht == 200.0
    assert invoice.total_vat == 30.0
    assert invoice.total_ttc == 230.0
