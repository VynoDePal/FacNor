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

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator, model_validator

from app.db import get_connection, initialize_database
from app.pdf import PdfInvoice, PdfInvoiceLine, build_invoice_pdf
from app.tax import TaxLineInput, calculate_invoice_totals, decimal_from_number


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("FACNOR_CORS_ORIGINS", "http://localhost:5173").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ClientBase(BaseModel):
    client_type: str = Field(default="b2c", pattern="^(b2b|b2c)$")
    name: str = Field(min_length=1)
    email: EmailStr | None = None
    address: str = Field(min_length=1)
    siren: str | None = None
    vat_number: str | None = None

    @field_validator("siren", "vat_number")
    @classmethod
    def normalize_business_identifiers(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = "".join(char for char in value.upper() if char.isalnum())
        return normalized or None

    @model_validator(mode="after")
    def validate_business_identifiers(self) -> "ClientBase":
        if self.client_type == "b2b":
            if self.siren is None or not is_valid_siren(self.siren):
                raise ValueError("A B2B client must provide a valid SIREN")
            if self.vat_number is None or not is_valid_french_vat_number(self.vat_number):
                raise ValueError("A B2B client must provide a valid French VAT number")
            if self.vat_number[4:] != self.siren:
                raise ValueError("VAT number must match the SIREN")
        return self


def is_valid_siren(siren: str) -> bool:
    if len(siren) != 9 or not siren.isdigit():
        return False
    total = 0
    parity = len(siren) % 2
    for index, char in enumerate(siren):
        digit = int(char)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def is_valid_french_vat_number(vat_number: str) -> bool:
    if len(vat_number) != 13 or not vat_number.startswith("FR") or not vat_number[2:].isdigit():
        return False
    siren = vat_number[4:]
    if not is_valid_siren(siren):
        return False
    expected_key = (12 + 3 * (int(siren) % 97)) % 97
    return vat_number[2:4] == f"{expected_key:02d}"


def serialize_client(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "client_type": row["client_type"],
        "name": row["name"],
        "email": row["email"],
        "address": row["address"],
        "siren": row["siren"],
        "vat_number": row["vat_number"],
        "created_at": row["created_at"],
    }



def serialize_invoice_line(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "invoice_id": row["invoice_id"],
        "description": row["description"],
        "quantity": row["quantity"],
        "unit_price": row["unit_price"],
        "tax_rate": row["tax_rate"],
        "line_total_excluding_tax": row["line_total_excluding_tax"],
        "line_total_tax": row["line_total_tax"],
        "line_total_including_tax": row["line_total_including_tax"],
    }


def serialize_invoice(row: sqlite3.Row, lines: list[sqlite3.Row] | None = None) -> dict[str, object]:
    invoice = {
        "id": row["id"],
        "user_id": row["user_id"],
        "client_id": row["client_id"],
        "invoice_number": row["invoice_number"],
        "issue_date": row["issue_date"],
        "due_date": row["due_date"],
        "status": row["status"],
        "currency": row["currency"],
        "total_excluding_tax": row["total_excluding_tax"],
        "total_tax": row["total_tax"],
        "total_including_tax": row["total_including_tax"],
        "created_at": row["created_at"],
    }
    if lines is not None:
        invoice["lines"] = [serialize_invoice_line(line) for line in lines]
    return invoice


def fetch_invoice_lines(connection: sqlite3.Connection, invoice_id: int, user_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT invoice_lines.id, invoice_lines.invoice_id, invoice_lines.description,
               invoice_lines.quantity, invoice_lines.unit_price, invoice_lines.tax_rate,
               invoice_lines.line_total_excluding_tax, invoice_lines.line_total_tax,
               invoice_lines.line_total_including_tax
        FROM invoice_lines
        INNER JOIN invoices ON invoices.id = invoice_lines.invoice_id
        WHERE invoice_lines.invoice_id = ? AND invoices.user_id = ?
        ORDER BY invoice_lines.id
        """,
        (invoice_id, user_id),
    ).fetchall()


def fetch_invoice_with_client(
    connection: sqlite3.Connection, invoice_id: int, user_id: int
) -> tuple[sqlite3.Row, list[sqlite3.Row]] | None:
    row = connection.execute(
        """
        SELECT invoices.id, invoices.user_id, invoices.client_id, invoices.invoice_number,
               invoices.issue_date, invoices.due_date, invoices.status, invoices.currency,
               invoices.total_excluding_tax, invoices.total_tax, invoices.total_including_tax,
               invoices.created_at, users.full_name AS issuer_name, users.email AS issuer_email,
               clients.name AS client_name, clients.email AS client_email, clients.address AS client_address
        FROM invoices
        INNER JOIN users ON users.id = invoices.user_id
        INNER JOIN clients ON clients.id = invoices.client_id AND clients.user_id = invoices.user_id
        WHERE invoices.id = ? AND invoices.user_id = ?
        """,
        (invoice_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return row, fetch_invoice_lines(connection, invoice_id, user_id)


def next_invoice_number(connection: sqlite3.Connection, user_id: int, issue_date: date) -> str:
    year = issue_date.year
    row = connection.execute(
        "SELECT next_number FROM invoice_sequences WHERE user_id = ? AND sequence_year = ?",
        (user_id, year),
    ).fetchone()
    if row is None:
        next_number = 1
        connection.execute(
            "INSERT INTO invoice_sequences (user_id, sequence_year, next_number) VALUES (?, ?, ?)",
            (user_id, year, 2),
        )
    else:
        next_number = row["next_number"]
        connection.execute(
            "UPDATE invoice_sequences SET next_number = ? WHERE user_id = ? AND sequence_year = ?",
            (next_number + 1, user_id, year),
        )
    return f"FAC-{year}-{next_number:04d}"


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    client_type: str | None = Field(default=None, pattern="^(b2b|b2c)$")
    name: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None
    address: str | None = Field(default=None, min_length=1)
    siren: str | None = None
    vat_number: str | None = None

    @field_validator("siren", "vat_number")
    @classmethod
    def normalize_business_identifiers(cls, value: str | None) -> str | None:
        return ClientBase.normalize_business_identifiers(value)


class InvoiceLineCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(default=20, ge=0)


class InvoiceCreate(BaseModel):
    client_id: int
    invoice_number: str | None = Field(default=None, min_length=1)
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
def login(payload: UserLogin, connection: sqlite3.Connection = Depends(get_connection)) -> dict[str, object]:
    user = connection.execute(
        "SELECT id, email, full_name, password_salt, password_hash FROM users WHERE email = ?",
        (payload.email,),
    ).fetchone()
    if user is None or not verify_password(payload.password, user["password_salt"], user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "access_token": create_access_token(user["id"], user["email"]),
        "token_type": "bearer",
    }


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
            INSERT INTO clients (user_id, client_type, name, email, address, siren, vat_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, payload.client_type, payload.name, payload.email, payload.address, payload.siren, payload.vat_number),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Invalid client data") from exc

    row = connection.execute(
        "SELECT id, user_id, client_type, name, email, address, siren, vat_number, created_at FROM clients WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return serialize_client(row)


@app.get("/clients")
def list_clients(
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT id, user_id, client_type, name, email, address, siren, vat_number, created_at
        FROM clients
        WHERE user_id = ?
        ORDER BY id
        """,
        (current_user["id"],),
    ).fetchall()
    return [serialize_client(row) for row in rows]


@app.get("/clients/{client_id}")
def get_client(
    client_id: int,
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    row = connection.execute(
        """
        SELECT id, user_id, client_type, name, email, address, siren, vat_number, created_at
        FROM clients
        WHERE id = ? AND user_id = ?
        """,
        (client_id, current_user["id"]),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return serialize_client(row)


@app.put("/clients/{client_id}")
def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    existing = connection.execute(
        """
        SELECT id, user_id, client_type, name, email, address, siren, vat_number, created_at
        FROM clients
        WHERE id = ? AND user_id = ?
        """,
        (client_id, current_user["id"]),
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    try:
        merged = ClientCreate(
            client_type=payload.client_type if payload.client_type is not None else existing["client_type"],
            name=payload.name if payload.name is not None else existing["name"],
            email=payload.email if payload.email is not None else existing["email"],
            address=payload.address if payload.address is not None else existing["address"],
            siren=payload.siren if payload.siren is not None else existing["siren"],
            vat_number=payload.vat_number if payload.vat_number is not None else existing["vat_number"],
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    connection.execute(
        """
        UPDATE clients
        SET client_type = ?, name = ?, email = ?, address = ?, siren = ?, vat_number = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            merged.client_type,
            merged.name,
            merged.email,
            merged.address,
            merged.siren,
            merged.vat_number,
            client_id,
            current_user["id"],
        ),
    )
    connection.commit()
    row = connection.execute(
        """
        SELECT id, user_id, client_type, name, email, address, siren, vat_number, created_at
        FROM clients
        WHERE id = ? AND user_id = ?
        """,
        (client_id, current_user["id"]),
    ).fetchone()
    return serialize_client(row)


@app.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> None:
    cursor = connection.execute("DELETE FROM clients WHERE id = ? AND user_id = ?", (client_id, current_user["id"]))
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")


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

    if payload.invoice_number is not None:
        existing_invoice = connection.execute(
            "SELECT id FROM invoices WHERE user_id = ? AND invoice_number = ?",
            (user_id, payload.invoice_number),
        ).fetchone()
        if existing_invoice is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice number already exists")

    tax_totals = calculate_invoice_totals(
        [
            TaxLineInput(
                quantity=decimal_from_number(line.quantity),
                unit_price=decimal_from_number(line.unit_price),
                tax_rate=decimal_from_number(line.tax_rate),
            )
            for line in payload.lines
        ]
    )

    try:
        connection.execute("BEGIN IMMEDIATE")
        invoice_number = payload.invoice_number or next_invoice_number(connection, user_id, payload.issue_date)
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
                invoice_number,
                payload.issue_date.isoformat(),
                payload.due_date.isoformat() if payload.due_date else None,
                float(tax_totals.total_excluding_tax),
                float(tax_totals.total_tax),
                float(tax_totals.total_including_tax),
            ),
        )
        invoice_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO invoice_lines (
                invoice_id, description, quantity, unit_price, tax_rate,
                line_total_excluding_tax, line_total_tax, line_total_including_tax
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    invoice_id,
                    line.description,
                    line.quantity,
                    line.unit_price,
                    line.tax_rate,
                    float(line_totals.total_excluding_tax),
                    float(line_totals.total_tax),
                    float(line_totals.total_including_tax),
                )
                for line, line_totals in zip(payload.lines, tax_totals.lines, strict=True)
            ],
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice number already exists") from exc
        raise HTTPException(status_code=400, detail="Invalid invoice data") from exc

    row = connection.execute(
        """
        SELECT id, user_id, client_id, invoice_number, issue_date, due_date, status, currency,
               total_excluding_tax, total_tax, total_including_tax, created_at
        FROM invoices
        WHERE id = ? AND user_id = ?
        """,
        (invoice_id, user_id),
    ).fetchone()
    lines = fetch_invoice_lines(connection, invoice_id, user_id)
    return serialize_invoice(row, lines)


@app.get("/invoices")
def list_invoices(
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT id, user_id, client_id, invoice_number, issue_date, due_date, status, currency,
               total_excluding_tax, total_tax, total_including_tax, created_at
        FROM invoices
        WHERE user_id = ?
        ORDER BY issue_date, id
        """,
        (current_user["id"],),
    ).fetchall()
    return [serialize_invoice(row) for row in rows]


@app.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict[str, object]:
    row = connection.execute(
        """
        SELECT id, user_id, client_id, invoice_number, issue_date, due_date, status, currency,
               total_excluding_tax, total_tax, total_including_tax, created_at
        FROM invoices
        WHERE id = ? AND user_id = ?
        """,
        (invoice_id, current_user["id"]),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    lines = fetch_invoice_lines(connection, invoice_id, current_user["id"])
    return serialize_invoice(row, lines)


@app.get("/invoices/{invoice_id}/pdf")
def export_invoice_pdf(
    invoice_id: int,
    current_user: Annotated[sqlite3.Row, Depends(get_current_user)],
    connection: sqlite3.Connection = Depends(get_connection),
) -> Response:
    invoice_data = fetch_invoice_with_client(connection, invoice_id, current_user["id"])
    if invoice_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    row, lines = invoice_data
    pdf_invoice = PdfInvoice(
        issuer_name=row["issuer_name"],
        issuer_email=row["issuer_email"],
        client_name=row["client_name"],
        client_email=row["client_email"],
        client_address=row["client_address"],
        invoice_number=row["invoice_number"],
        issue_date=row["issue_date"],
        due_date=row["due_date"],
        currency=row["currency"],
        lines=[
            PdfInvoiceLine(
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                tax_rate=line["tax_rate"],
                total_excluding_tax=line["line_total_excluding_tax"],
                total_tax=line["line_total_tax"],
                total_including_tax=line["line_total_including_tax"],
            )
            for line in lines
        ],
        total_excluding_tax=row["total_excluding_tax"],
        total_tax=row["total_tax"],
        total_including_tax=row["total_including_tax"],
    )
    filename = f"facture-{row['invoice_number']}.pdf"
    return Response(
        content=build_invoice_pdf(pdf_invoice),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

