from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Client, ClientType, Invoice, InvoiceItem, User


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def test_schema_contains_required_tables(session):
    tables = set(inspect(session.bind).get_table_names())
    assert {"users", "clients", "invoices", "invoice_items"}.issubset(tables)


def test_can_create_b2b_client_invoice_and_items(session):
    user = User(email="owner@example.com", hashed_password="hashed")
    client = Client(
        user=user,
        client_type=ClientType.b2b,
        name="Entreprise SAS",
        address_line1="1 rue Exemple",
        postal_code="75001",
        city="Paris",
        siren="123456789",
    )
    invoice = Invoice(
        user=user,
        client=client,
        number="FAC-2025-0001",
        issue_date=date(2025, 6, 19),
        total_ht=Decimal("100.00"),
        total_tva=Decimal("20.00"),
        total_ttc=Decimal("120.00"),
    )
    item = InvoiceItem(
        invoice=invoice,
        position=1,
        description="Prestation",
        quantity=Decimal("1.000"),
        unit_price_ht=Decimal("100.00"),
        vat_rate=Decimal("20.00"),
        line_total_ht=Decimal("100.00"),
        line_total_tva=Decimal("20.00"),
        line_total_ttc=Decimal("120.00"),
    )
    session.add(item)
    session.commit()

    assert invoice.id is not None
    assert invoice.items[0].description == "Prestation"
    assert client.client_type == ClientType.b2b


def test_b2b_client_requires_siren_or_vat(session):
    session.add(User(email="owner@example.com", hashed_password="hashed"))
    session.flush()
    user = session.query(User).one()
    session.add(
        Client(
            user_id=user.id,
            client_type=ClientType.b2b,
            name="Entreprise SAS",
            address_line1="1 rue Exemple",
            postal_code="75001",
            city="Paris",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_invoice_number_is_unique_per_user(session):
    user = User(email="owner@example.com", hashed_password="hashed")
    client = Client(
        user=user,
        client_type=ClientType.b2c,
        name="Client Particulier",
        address_line1="2 rue Exemple",
        postal_code="69001",
        city="Lyon",
    )
    session.add_all(
        [
            Invoice(user=user, client=client, number="FAC-1", issue_date=date.today()),
            Invoice(user=user, client=client, number="FAC-1", issue_date=date.today()),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()
