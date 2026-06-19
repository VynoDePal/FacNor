from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.app.database import Base
from backend.app.models import Client, Invoice, InvoiceItem, User


def test_database_schema_creates_required_tables_and_relationships() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)

    assert {"users", "clients", "invoices", "invoice_items"}.issubset(set(inspector.get_table_names()))
    assert _foreign_keys(inspector, "clients") == {"user_id": "users"}
    assert _foreign_keys(inspector, "invoices") == {"user_id": "users", "client_id": "clients"}
    assert _foreign_keys(inspector, "invoice_items") == {"invoice_id": "invoices"}


def test_database_relationships_allow_invoice_with_items() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        user = User(
            email="owner@example.com",
            hashed_password="hashed-password",
            company_name="FacNor SAS",
            address="1 rue de Paris, 75000 Paris",
        )
        client = Client(
            user=user,
            name="Client Exemple",
            client_type="business",
            siren="123456789",
            address="2 avenue de Lyon, 69000 Lyon",
        )
        invoice = Invoice(user=user, client=client, number="2025-0001")
        invoice.items.append(
            InvoiceItem(
                position=1,
                description="Prestation de service",
                quantity=2,
                unit_price_excluding_tax=100,
                vat_rate=20,
                total_excluding_tax=200,
                total_tax=40,
                total_including_tax=240,
            )
        )

        session.add(invoice)
        session.commit()
        session.refresh(invoice)

        assert invoice.user.email == "owner@example.com"
        assert invoice.client.name == "Client Exemple"
        assert invoice.items[0].invoice_id == invoice.id


def _foreign_keys(inspector, table_name: str) -> dict[str, str]:
    return {
        constrained_column: foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys(table_name)
        for constrained_column in foreign_key["constrained_columns"]
    }
