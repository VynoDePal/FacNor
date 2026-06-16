from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import hmac
import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlite3 import Connection, IntegrityError

from app.db import connect, create_invoice, init_db, row_to_dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = init_db(connect())
    app.state.db = connection
    try:
        yield
    finally:
        connection.close()




def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 100_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, password_hash)
    _, salt, digest = password_hash.split("$", 2)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 100_000).hex()
    return hmac.compare_digest(candidate, digest)


app = FastAPI(title="FacNor API", lifespan=lifespan)


class UserCreate(BaseModel):
    email: str
    full_name: str
    password_hash: str
    company_name: str | None = None
    siren: str | None = None
    vat_number: str | None = None



class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    company_name: str | None = None
    siren: str | None = None
    vat_number: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ClientCreate(BaseModel):
    user_id: int
    name: str
    email: str | None = None
    address: str
    postal_code: str
    city: str
    country: str = "France"
    siren: str | None = None
    vat_number: str | None = None


class InvoiceLineCreate(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit_price_excluding_tax: int = Field(ge=0)
    vat_rate: float = Field(ge=0)


class InvoiceCreate(BaseModel):
    user_id: int
    client_id: int
    issue_date: str | None = None
    due_date: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


def get_db() -> Connection:
    return app.state.db


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "FacNor API", "status": "ok"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Annotated[Connection, Depends(get_db)]) -> dict:
    try:
        cursor = db.execute(
            """
            INSERT INTO users (email, full_name, password_hash, company_name, siren, vat_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.email,
                payload.full_name or payload.email,
                hash_password(payload.password),
                payload.company_name,
                payload.siren,
                payload.vat_number,
            ),
        )
        db.commit()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    user = row_to_dict(db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())
    user.pop("password_hash", None)
    return user


@app.post("/auth/login")
def login(payload: LoginRequest, db: Annotated[Connection, Depends(get_db)]) -> dict:
    user = db.execute("SELECT * FROM users WHERE email = ?", (payload.email,)).fetchone()
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": f"dev-token-{user['id']}", "token_type": "bearer", "user_id": user["id"]}



@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Annotated[Connection, Depends(get_db)]) -> dict:
    try:
        cursor = db.execute(
            """
            INSERT INTO users (email, full_name, password_hash, company_name, siren, vat_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.email,
                payload.full_name,
                payload.password_hash,
                payload.company_name,
                payload.siren,
                payload.vat_number,
            ),
        )
        db.commit()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return row_to_dict(db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())


@app.post("/clients", status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Annotated[Connection, Depends(get_db)]) -> dict:
    try:
        cursor = db.execute(
            """
            INSERT INTO clients (user_id, name, email, address, postal_code, city, country, siren, vat_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.user_id,
                payload.name,
                payload.email,
                payload.address,
                payload.postal_code,
                payload.city,
                payload.country,
                payload.siren,
                payload.vat_number,
            ),
        )
        db.commit()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return row_to_dict(db.execute("SELECT * FROM clients WHERE id = ?", (cursor.lastrowid,)).fetchone())


@app.post("/invoices", status_code=status.HTTP_201_CREATED)
def post_invoice(payload: InvoiceCreate, db: Annotated[Connection, Depends(get_db)]) -> dict:
    try:
        return create_invoice(
            db,
            user_id=payload.user_id,
            client_id=payload.client_id,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            lines=[line.model_dump() if hasattr(line, "model_dump") else line.dict() for line in payload.lines],
        )
    except (IntegrityError, ValueError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
