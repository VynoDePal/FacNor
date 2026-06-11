from datetime import date
import pytest
from decimal import Decimal
from app.services.calculator import InvoiceCalculator
from app.services.numbering import InvoiceNumberingService
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.user import User
from app.models.client import Client

def test_vat_calculation_precision():
    # Test case: 3 items with different VAT rates and precision issues
    items = [
        InvoiceItem(quantity=1, unit_price_ht=10.333, vat_rate=20.0), # 10.33 * 0.2 = 2.066 -> 2.07
        InvoiceItem(quantity=2, unit_price_ht=5.125, vat_rate=5.5),   # 10.25 * 0.055 = 0.56375 -> 0.56
        InvoiceItem(quantity=1, unit_price_ht=100.0, vat_rate=0.0),   # 100.0 * 0 = 0
    ]
    # Note: In the implementation, we quantize the line_ht first.
    # Item 1: line_ht = 10.33, vat = 10.33 * 0.2 = 2.066 -> 2.07
    # Item 2: line_ht = 10.25, vat = 10.25 * 0.055 = 0.56375 -> 0.56
    # Item 3: line_ht = 100.00, vat = 0
    # Total HT = 10.33 + 10.25 + 100.00 = 120.58
    # Total VAT = 2.07 + 0.56 + 0 = 2.63
    # Total TTC = 123.21

    totals = InvoiceCalculator.calculate_totals(items)
    assert totals["total_ht"] == 120.58
    assert totals["total_vat"] == 2.63
    assert totals["total_ttc"] == 123.21

def test_sequential_numbering(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="password")
    db_session.add(user)
    db_session.commit()

    # First invoice
    num1 = InvoiceNumberingService.generate_next_number(db_session, user.id)
    assert num1.endswith("0001")
    
    inv1 = Invoice(user_id=user.id, client_id=1, invoice_number=num1, date=date(2023, 1, 1))
    db_session.add(inv1)
    db_session.commit()

    # Second invoice
    num2 = InvoiceNumberingService.generate_next_number(db_session, user.id)
    assert num2.endswith("0002")
    
    inv2 = Invoice(user_id=user.id, client_id=1, invoice_number=num2, date=date(2023, 1, 2))
    db_session.add(inv2)
    db_session.commit()

def test_sequential_numbering_per_user(db_session):
    user1 = User(username="user1", email="user1@example.com", hashed_password="password")
    user2 = User(username="user2", email="user2@example.com", hashed_password="password")
    db_session.add_all([user1, user2])
    db_session.commit()

    # User 1's first invoice
    num1_u1 = InvoiceNumberingService.generate_next_number(db_session, user1.id)
    assert num1_u1.endswith("0001")
    db_session.add(Invoice(user_id=user1.id, client_id=1, invoice_number=num1_u1, date=date(2023, 1, 1)))
    db_session.commit()

    # User 2's first invoice
    num1_u2 = InvoiceNumberingService.generate_next_number(db_session, user2.id)
    assert num1_u2.endswith("0001")
    db_session.add(Invoice(user_id=user2.id, client_id=1, invoice_number=num1_u2, date=date(2023, 1, 1)))
    db_session.commit()

    # User 1's second invoice
    num2_u1 = InvoiceNumberingService.generate_next_number(db_session, user1.id)
    assert num2_u1.endswith("0002")
    db_session.add(Invoice(user_id=user1.id, client_id=1, invoice_number=num2_u1, date=date(2023, 1, 1)))
    db_session.commit()
