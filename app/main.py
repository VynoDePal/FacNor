from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

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
    client_id: int
    invoice_number: str = Field(min_length=1)
    issue_date: date
    due_date: date | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


security = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60


def get_jwt_secret() -> str:
    return os.getenv("FACNOR_JWT_SECRET", "facnor-development-secret-change-me")


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(UTC)
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRATION_MINUTES)).timestamp()),
    }
    signing_input = ".".join(
        [
            base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(get_jwt_secret().encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}"
        expected_signature = hmac.new(
            get_jwt_secret().encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        signature = base64url_decode(encoded_signature)
        header = json.loads(base64url_decode(encoded_header))
        payload = json.loads(base64url_decode(encoded_payload))
    except (binascii.Error, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    if header.get("alg") != JWT_ALGORITHM or not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("exp"), int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    if payload["exp"] < int(datetime.now(UTC).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token expired")
    return payload


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

    payload = decode_access_token(credentials.credentials)
    user = connection.execute(
        "SELECT id, email, full_name FROM users WHERE id = ?",
        (payload["sub"],),
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
    try:
        cursor = connection.execute(
            "INSERT INTO users (email, full_name, password_salt, password_hash, auth_token) VALUES (?, ?, ?, ?, ?)",
            (payload.email, payload.full_name, salt, password_hash, secrets.token_urlsafe(32)),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="User email already exists") from exc

    user_id = int(cursor.lastrowid)
    return {
        "id": user_id,
        "email": payload.email,
        "full_name": payload.full_name,
        "access_token": create_access_token(user_id, payload.email),
        "token_type": "bearer",
    }


@app.post("/auth/login")
def login(payload: UserLogin, connection: sqlite3.Connection = Depends(get_connection)) -> dict[str, str]:
    user = connection.execute(
        "SELECT id, email, password_salt, password_hash FROM users WHERE email = ?",
        (payload.email,),
    ).fetchone()
    if user is None or not verify_password(payload.password, user["password_salt"], user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {"access_token": create_access_token(user["id"], user["email"]), "token_type": "bearer"}


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

    existing_invoice = connection.execute(
        "SELECT id FROM invoices WHERE user_id = ? AND invoice_number = ?",
        (user_id, payload.invoice_number),
    ).fetchone()
    if existing_invoice is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice number already exists")

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
