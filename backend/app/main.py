from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth import create_access_token, get_current_user, hash_password, verify_password
from backend.app.database import get_db, init_db
from backend.app.invoice_numbering import generate_invoice_number
from backend.app.models import Client, Invoice, InvoiceItem, User


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str = Field(min_length=8)
    company_name: str = Field(min_length=1, max_length=255)
    siren: str | None = Field(default=None, min_length=9, max_length=9)
    vat_number: str | None = Field(default=None, max_length=32)
    address: str = Field(min_length=1)


class UserLogin(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str


class UserRead(BaseModel):
    id: int
    email: str
    company_name: str
    siren: str | None
    vat_number: str | None
    address: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    client_type: Literal["business", "individual"]
    siren: str | None = Field(default=None, pattern=r"^\d{9}$")
    vat_number: str | None = Field(default=None, max_length=32)
    address: str = Field(min_length=1)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    client_type: Literal["business", "individual"] | None = None
    siren: str | None = Field(default=None, pattern=r"^\d{9}$")
    vat_number: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, min_length=1)


class ClientRead(ClientBase):
    id: int

    model_config = {"from_attributes": True}


class InvoiceItemCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0, decimal_places=2)
    unit_price_excluding_tax: Decimal = Field(ge=0, decimal_places=2)
    vat_rate: Decimal = Field(ge=0, decimal_places=2)


class InvoiceCreate(BaseModel):
    client_id: int = Field(gt=0)
    issue_date: date | None = None
    due_date: date | None = None
    items: list[InvoiceItemCreate] = Field(min_length=1)


class InvoiceItemRead(BaseModel):
    id: int
    position: int
    description: str
    quantity: Decimal
    unit_price_excluding_tax: Decimal
    vat_rate: Decimal
    total_excluding_tax: Decimal
    total_tax: Decimal
    total_including_tax: Decimal

    model_config = {"from_attributes": True}


class InvoiceRead(BaseModel):
    id: int
    number: str
    issue_date: date
    due_date: date | None
    status: str
    client_id: int
    total_excluding_tax: Decimal
    total_tax: Decimal
    total_including_tax: Decimal
    items: list[InvoiceItemRead]

    model_config = {"from_attributes": True}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", tags=["health"])
def api_healthcheck() -> dict[str, str]:
    return healthcheck()


@app.get("/healthcheck", tags=["health"])
def healthcheck_alias() -> dict[str, str]:
    return healthcheck()


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"message": "FacNor API", "status": "ok"}


@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register_user(payload: UserCreate, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    existing_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        company_name=payload.company_name,
        siren=payload.siren,
        vat_number=payload.vat_number,
        address=payload.address,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
def login_user(payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@app.get("/api/auth/me", response_model=UserRead, tags=["auth"])
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@app.post("/api/clients", response_model=ClientRead, status_code=status.HTTP_201_CREATED, tags=["clients"])
def create_client(
    payload: ClientCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Client:
    client = Client(user_id=current_user.id, **payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@app.get("/api/clients", response_model=list[ClientRead], tags=["clients"])
def list_clients(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Client]:
    return list(db.scalars(select(Client).where(Client.user_id == current_user.id).order_by(Client.name, Client.id)))


@app.get("/api/clients/{client_id}", response_model=ClientRead, tags=["clients"])
def read_client(
    client_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Client:
    return _get_owned_client(db, client_id, current_user.id)


@app.put("/api/clients/{client_id}", response_model=ClientRead, tags=["clients"])
def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Client:
    client = _get_owned_client(db, client_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


@app.delete("/api/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["clients"])
def delete_client(
    client_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    client = _get_owned_client(db, client_id, current_user.id)
    db.delete(client)
    db.commit()


@app.post("/api/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED, tags=["invoices"])
def create_invoice(
    payload: InvoiceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    client = db.get(Client, payload.client_id)
    if client is None or client.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    invoice = Invoice(
        user_id=current_user.id,
        client_id=client.id,
        number=generate_invoice_number(db, current_user.id),
        issue_date=payload.issue_date or date.today(),
        due_date=payload.due_date,
    )

    total_excluding_tax = Decimal("0.00")
    total_tax = Decimal("0.00")
    total_including_tax = Decimal("0.00")
    for position, item_payload in enumerate(payload.items, start=1):
        item_total_excluding_tax = _money(item_payload.quantity * item_payload.unit_price_excluding_tax)
        item_total_tax = _money(item_total_excluding_tax * item_payload.vat_rate / Decimal("100"))
        item_total_including_tax = _money(item_total_excluding_tax + item_total_tax)
        invoice.items.append(
            InvoiceItem(
                position=position,
                description=item_payload.description,
                quantity=item_payload.quantity,
                unit_price_excluding_tax=item_payload.unit_price_excluding_tax,
                vat_rate=item_payload.vat_rate,
                total_excluding_tax=item_total_excluding_tax,
                total_tax=item_total_tax,
                total_including_tax=item_total_including_tax,
            )
        )
        total_excluding_tax += item_total_excluding_tax
        total_tax += item_total_tax
        total_including_tax += item_total_including_tax

    invoice.total_excluding_tax = _money(total_excluding_tax)
    invoice.total_tax = _money(total_tax)
    invoice.total_including_tax = _money(total_including_tax)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_owned_client(db: Session, client_id: int, user_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None or client.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client
