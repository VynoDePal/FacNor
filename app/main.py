from __future__ import annotations

from contextlib import asynccontextmanager
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlite3 import Connection, IntegrityError

from app.db import connect, create_invoice, init_db, row_to_dict

TOKEN_TTL_SECONDS = 60 * 60 * 24
TOKEN_SECRET = os.getenv("AUTH_SECRET", "facnor-development-secret")
security_scheme = HTTPBearer(auto_error=False)


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
    try:
        _, salt, digest = password_hash.split("$", 2)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 100_000).hex()
    return hmac.compare_digest(candidate, digest)


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        "nonce": secrets.token_hex(8),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def _decode_token_payload(token: str) -> dict:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    expected_signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    actual_signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
    payload = json.loads(payload_bytes.decode("utf-8"))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Expired token")
    return payload


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
    password: str = Field(min_length=1)
    full_name: str | None = None
    company_name: str | None = None
    siren: str | None = None
    vat_number: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ClientCreate(BaseModel):
    user_id: int | None = None
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
    user_id: int | None = None
    client_id: int
    issue_date: str | None = None
    due_date: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


def get_db() -> Connection:
    return app.state.db


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    db: Annotated[Connection, Depends(get_db)],
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = _decode_token_payload(credentials.credentials)
    user_id = int(payload["sub"])
    user = row_to_dict(db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user.pop("password_hash", None)
    return user


def _token_response(user: dict) -> dict:
    safe_user = dict(user)
    safe_user.pop("password_hash", None)
    return {
        "access_token": create_access_token(int(user["id"])),
        "token_type": "bearer",
        "user_id": user["id"],
        "user": safe_user,
    }


def _resolve_authenticated_user_id(payload_user_id: int | None, current_user: dict) -> int:
    user_id = int(current_user["id"])
    if payload_user_id is not None and payload_user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Cannot act for another user")
    return user_id


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
    return _token_response(user)


@app.post("/auth/login")
def login(payload: LoginRequest, db: Annotated[Connection, Depends(get_db)]) -> dict:
    user = row_to_dict(db.execute("SELECT * FROM users WHERE email = ?", (payload.email,)).fetchone())
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _token_response(user)


@app.get("/auth/me")
def me(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return current_user


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
    user = row_to_dict(db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())
    user.pop("password_hash", None)
    return user


@app.post("/clients", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    user_id = _resolve_authenticated_user_id(payload.user_id, current_user)
    try:
        cursor = db.execute(
            """
            INSERT INTO clients (user_id, name, email, address, postal_code, city, country, siren, vat_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
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
def post_invoice(
    payload: InvoiceCreate,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    user_id = _resolve_authenticated_user_id(payload.user_id, current_user)
    client_owner = db.execute(
        "SELECT user_id FROM clients WHERE id = ?",
        (payload.client_id,),
    ).fetchone()
    if client_owner is None or int(client_owner["user_id"]) != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found")
    try:
        return create_invoice(
            db,
            user_id=user_id,
            client_id=payload.client_id,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            lines=[line.model_dump() if hasattr(line, "model_dump") else line.dict() for line in payload.lines],
        )
    except (IntegrityError, ValueError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
