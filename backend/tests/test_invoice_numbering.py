from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.invoice_numbering import generate_invoice_number
from backend.app.models import Client, Invoice, User
from backend.main import app

USER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "secure-password",
    "company_name": "FacNor SAS",
    "siren": "123456789",
    "vat_number": "FR12345678901",
    "address": "1 rue de Paris, 75000 Paris",
}


def test_invoice_numbers_are_sequential_per_user() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        first_user = _add_user(session, "first@example.com")
        second_user = _add_user(session, "second@example.com")
        session.commit()

        assert generate_invoice_number(session, first_user.id) == "0001"
        assert generate_invoice_number(session, first_user.id) == "0002"
        assert generate_invoice_number(session, second_user.id) == "0001"


def test_rolled_back_invoice_number_is_reused_without_gap() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        user = _add_user(session, "owner@example.com")
        client = _add_client(session, user)
        session.commit()

        invoice = Invoice(user_id=user.id, client_id=client.id, number=generate_invoice_number(session, user.id))
        session.add(invoice)
        session.flush()
        assert invoice.number == "0001"
        session.rollback()

        invoice = Invoice(user_id=user.id, client_id=client.id, number=generate_invoice_number(session, user.id))
        session.add(invoice)
        session.commit()
        assert invoice.number == "0001"


def test_create_invoice_endpoint_assigns_next_number_and_totals() -> None:
    with invoice_client() as client:
        register_body = client.post("/api/auth/register", json=USER_PAYLOAD).json()
        token = register_body["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client_id = _create_client_for_user(client.app_state["session_factory"], register_body["user"]["id"])

        first_response = client.post("/api/invoices", json=_invoice_payload(client_id), headers=headers)
        second_response = client.post("/api/invoices", json=_invoice_payload(client_id), headers=headers)

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        first_invoice = first_response.json()
        second_invoice = second_response.json()
        assert first_invoice["number"] == "0001"
        assert second_invoice["number"] == "0002"
        assert first_invoice["total_excluding_tax"] == "200.00"
        assert first_invoice["total_tax"] == "40.00"
        assert first_invoice["total_including_tax"] == "240.00"


def test_create_invoice_requires_authentication() -> None:
    with invoice_client() as client:
        response = client.post("/api/invoices", json=_invoice_payload(client.app_state["client_id"]))

        assert response.status_code == 401


class invoice_client:
    def __enter__(self) -> TestClient:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def override_get_db() -> Generator[Session, None, None]:
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.client.app_state["session_factory"] = TestingSessionLocal
        self.client.app_state["client_id"] = 1
        return self.client

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        app.dependency_overrides.clear()


def _invoice_payload(client_id: int) -> dict[str, object]:
    return {
        "client_id": client_id,
        "items": [
            {
                "description": "Prestation de service",
                "quantity": "2.00",
                "unit_price_excluding_tax": "100.00",
                "vat_rate": "20.00",
            }
        ],
    }


def _add_user(session: Session, email: str) -> User:
    user = User(
        email=email,
        hashed_password="hashed-password",
        company_name="FacNor SAS",
        address="1 rue de Paris, 75000 Paris",
    )
    session.add(user)
    session.flush()
    return user



def _create_client_for_user(session_factory: sessionmaker[Session], user_id: int) -> int:
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        client = _add_client(session, user)
        session.commit()
        return client.id


def _add_client(session: Session, user: User) -> Client:
    client = Client(
        user_id=user.id,
        name="Client Exemple",
        client_type="business",
        siren="123456789",
        address="2 avenue de Lyon, 69000 Lyon",
    )
    session.add(client)
    session.flush()
    return client
