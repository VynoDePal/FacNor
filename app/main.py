from __future__ import annotations

import hashlib
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from app.db import get_connection, initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ClientCreate(BaseModel):
    user_id: int | None = None
    name: str = Field(min_length=1)
    email: EmailStr | None = None
    address: str = Field(min_length=1)
    vat_number: str | None = None


class InvoiceLineCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(default=20, ge=0)


class InvoiceCreate(BaseModel):
    user_id: int | None = None
    client_id: int
    invoice_number: str = Field(min_length=1)
    issue_date: date
    due_date: date | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


security = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return salt, digest.hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, candidate_hash = hash_password(password, salt)
    return secrets.compare_digest(candidate_hash, password_hash)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> sqlite3.Row:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = connection.execute(
        "SELECT id, email, full_name FROM users WHERE auth_token = ?",
        (credentials.credentials,),
    ).fetchone()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    return user


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, connection: sqlite3.Connection = Depends(get_connection)) -> dict[str, object]:
    salt, password_hash = hash_password(payload.password)
    auth_token = secrets.token_urlsafe(32)
    try:
        cursor = connection.execute(
            "INSERT INTO users (email, full_name, password_salt, password_hash, auth_token) VALUES (?, ?, ?, ?, ?)",
            (payload.email, payload.full_name, salt, password_hash, auth_token),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="User email already exists") from exc

    return {"id": cursor.lastrowid, "email": payload.email, "full_name": payload.full_name, "access_token": auth_token}


@app.post("/auth/login")
def login(payload: UserLogin, connection: sqlite3.Connection = Depends(get_connection)) -> dict[str, str]:
    user = connection.execute(
        "SELECT id, password_salt, password_hash FROM users WHERE email = ?",
        (payload.email,),
    ).fetchone()
    if user is None or not verify_password(payload.password, user["password_salt"], user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    auth_token = secrets.token_urlsafe(32)
    connection.execute("UPDATE users SET auth_token = ? WHERE id = ?", (auth_token, user["id"]))
    connection.commit()
    return {"access_token": auth_token, "token_type": "bearer"}


@app.post("/clients", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    user_id = current_user["id"]
    try:
        cursor = connection.execute(
            """
            INSERT INTO clients (user_id, name, email, address, vat_number)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, payload.name, payload.email, payload.address, payload.vat_number),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Invalid client owner") from exc

    return {
        "id": cursor.lastrowid,
        "user_id": user_id,
        "name": payload.name,
        "email": payload.email,
        "address": payload.address,
        "vat_number": payload.vat_number,
    }


@app.post("/invoices", status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    user_id = current_user["id"]
    client = connection.execute(
        "SELECT id FROM clients WHERE id = ? AND user_id = ?",
        (payload.client_id, user_id),
    ).fetchone()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    total_excluding_tax = sum(line.quantity * line.unit_price for line in payload.lines)
    total_tax = sum(line.quantity * line.unit_price * line.tax_rate / 100 for line in payload.lines)
    total_including_tax = total_excluding_tax + total_tax

    try:
        cursor = connection.execute(
            """
            INSERT INTO invoices (
                user_id, client_id, invoice_number, issue_date, due_date,
                total_excluding_tax, total_tax, total_including_tax
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                payload.client_id,
                payload.invoice_number,
                payload.issue_date.isoformat(),
                payload.due_date.isoformat() if payload.due_date else None,
                total_excluding_tax,
                total_tax,
                total_including_tax,
            ),
        )
        invoice_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO invoice_lines (
                invoice_id, description, quantity, unit_price, tax_rate, line_total_excluding_tax
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    invoice_id,
                    line.description,
                    line.quantity,
                    line.unit_price,
                    line.tax_rate,
                    line.quantity * line.unit_price,
                )
                for line in payload.lines
            ],
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=400, detail="Invalid invoice data") from exc

    return {
        "id": invoice_id,
        "invoice_number": payload.invoice_number,
        "total_excluding_tax": total_excluding_tax,
        "total_tax": total_tax,
        "total_including_tax": total_including_tax,
    }
