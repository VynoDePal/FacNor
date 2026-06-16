from __future__ import annotations

from contextlib import asynccontextmanager
import base64
from io import BytesIO
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlite3 import Connection, IntegrityError

from app.db import connect, create_invoice, get_invoice, init_db, row_to_dict, update_invoice
from app.pdf import generate_invoice_pdf

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
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


class InvoiceUpdate(BaseModel):
    client_id: int | None = None
    issue_date: str | None = None
    due_date: str | None = None
    status: str | None = None
    lines: list[InvoiceLineCreate] | None = None


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


def _get_owned_client(db: Connection, client_id: int, user_id: int) -> dict:
    client = row_to_dict(
        db.execute(
            "SELECT * FROM clients WHERE id = ? AND user_id = ?",
            (client_id, user_id),
        ).fetchone()
    )
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def _ensure_owned_client(db: Connection, client_id: int, user_id: int) -> None:
    _get_owned_client(db, client_id, user_id)


def _get_owned_invoice(db: Connection, invoice_id: int, user_id: int) -> dict:
    invoice = get_invoice(db, invoice_id)
    if invoice is None or int(invoice["user_id"]) != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _invoice_lines_payload(lines: list[InvoiceLineCreate]) -> list[dict]:
    return [line.model_dump() for line in lines]


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "FacNor API", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    return _get_owned_client(db, int(cursor.lastrowid), user_id)


@app.get("/clients")
def list_clients(
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> list[dict]:
    return [
        dict(row)
        for row in db.execute(
            "SELECT * FROM clients WHERE user_id = ? ORDER BY id",
            (current_user["id"],),
        ).fetchall()
    ]


@app.get("/clients/{client_id}")
def get_client(
    client_id: int,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _get_owned_client(db, client_id, int(current_user["id"]))


@app.put("/clients/{client_id}")
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    user_id = int(current_user["id"])
    _get_owned_client(db, client_id, user_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _get_owned_client(db, client_id, user_id)

    assignments = ", ".join(f"{field} = ?" for field in updates)
    try:
        db.execute(
            f"UPDATE clients SET {assignments} WHERE id = ? AND user_id = ?",
            (*updates.values(), client_id, user_id),
        )
        db.commit()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _get_owned_client(db, client_id, user_id)


@app.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Response:
    user_id = int(current_user["id"])
    _get_owned_client(db, client_id, user_id)
    try:
        db.execute("DELETE FROM clients WHERE id = ? AND user_id = ?", (client_id, user_id))
        db.commit()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/invoices", status_code=status.HTTP_201_CREATED)
def post_invoice(
    payload: InvoiceCreate,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    user_id = _resolve_authenticated_user_id(payload.user_id, current_user)
    _ensure_owned_client(db, payload.client_id, user_id)
    try:
        return create_invoice(
            db,
            user_id=user_id,
            client_id=payload.client_id,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            lines=_invoice_lines_payload(payload.lines),
        )
    except (IntegrityError, ValueError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/invoices")
def list_invoices(
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> list[dict]:
    invoice_ids = [
        row["id"]
        for row in db.execute(
            "SELECT id FROM invoices WHERE user_id = ? ORDER BY id",
            (current_user["id"],),
        ).fetchall()
    ]
    return [get_invoice(db, int(invoice_id)) for invoice_id in invoice_ids]


@app.get("/invoices/{invoice_id}/pdf")
def export_invoice_pdf(
    invoice_id: int,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> StreamingResponse:
    invoice = _get_owned_invoice(db, invoice_id, int(current_user["id"]))
    pdf = generate_invoice_pdf(db, invoice_id)
    if pdf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    filename = f"facture-{invoice['invoice_number']}.pdf"
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/invoices/{invoice_id}")
def read_invoice(
    invoice_id: int,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return _get_owned_invoice(db, invoice_id, int(current_user["id"]))


@app.put("/invoices/{invoice_id}")
def put_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    user_id = int(current_user["id"])
    _get_owned_invoice(db, invoice_id, user_id)
    if payload.client_id is not None:
        _ensure_owned_client(db, payload.client_id, user_id)
    try:
        updated = update_invoice(
            db,
            invoice_id,
            client_id=payload.client_id,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            status=payload.status,
            lines=None if payload.lines is None else _invoice_lines_payload(payload.lines),
        )
    except (IntegrityError, ValueError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return updated


@app.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: int,
    db: Annotated[Connection, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Response:
    user_id = int(current_user["id"])
    _get_owned_invoice(db, invoice_id, user_id)
    db.execute("DELETE FROM invoices WHERE id = ? AND user_id = ?", (invoice_id, user_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
