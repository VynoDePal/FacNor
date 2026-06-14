from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import UserResponse, get_current_user
from app.database import get_connection

router = APIRouter(prefix="/invoices", tags=["invoices"])


class InvoiceCreate(BaseModel):
    client_id: int
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None


class InvoiceResponse(BaseModel):
    id: int
    user_id: int
    client_id: int
    invoice_number: str
    issue_date: str
    due_date: str | None = None
    status: str
    total_excluding_tax: Decimal
    total_vat: Decimal
    total_including_tax: Decimal
    created_at: str


INVOICE_NUMBER_PREFIX = "FAC"
INVOICE_NUMBER_WIDTH = 6
INVOICE_SEQUENCE_NAME = "global_invoice_number"


def format_invoice_number(sequence_number: int) -> str:
    if sequence_number < 1:
        raise ValueError("Le numéro de séquence doit être positif.")
    return f"{INVOICE_NUMBER_PREFIX}-{sequence_number:0{INVOICE_NUMBER_WIDTH}d}"


def _invoice_response(row) -> InvoiceResponse:
    return InvoiceResponse(
        id=row["id"],
        user_id=row["user_id"],
        client_id=row["client_id"],
        invoice_number=row["invoice_number"],
        issue_date=row["issue_date"],
        due_date=row["due_date"],
        status=row["status"],
        total_excluding_tax=Decimal(str(row["total_excluding_tax"])),
        total_vat=Decimal(str(row["total_vat"])),
        total_including_tax=Decimal(str(row["total_including_tax"])),
        created_at=row["created_at"],
    )


def _reserve_invoice_number(connection) -> str:
    row = connection.execute(
        "SELECT next_number FROM invoice_number_sequences WHERE name = ?",
        (INVOICE_SEQUENCE_NAME,),
    ).fetchone()

    if row is None:
        sequence_number = 1
        connection.execute(
            """
            INSERT INTO invoice_number_sequences (name, next_number)
            VALUES (?, ?)
            """,
            (INVOICE_SEQUENCE_NAME, 2),
        )
    else:
        sequence_number = row["next_number"]
        connection.execute(
            """
            UPDATE invoice_number_sequences
            SET next_number = ?, updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
            """,
            (sequence_number + 1, INVOICE_SEQUENCE_NAME),
        )

    return format_invoice_number(sequence_number)


def _ensure_client_belongs_to_user(connection, client_id: int, user_id: int) -> None:
    row = connection.execute(
        "SELECT id FROM clients WHERE id = ? AND user_id = ?",
        (client_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable.")


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> InvoiceResponse:
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_client_belongs_to_user(connection, payload.client_id, current_user.id)
        invoice_number = _reserve_invoice_number(connection)
        cursor = connection.execute(
            """
            INSERT INTO invoices (user_id, client_id, invoice_number, issue_date, due_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                payload.client_id,
                invoice_number,
                payload.issue_date.isoformat(),
                payload.due_date.isoformat() if payload.due_date else None,
            ),
        )
        row = connection.execute(
            """
            SELECT id, user_id, client_id, invoice_number, issue_date, due_date, status,
                   total_excluding_tax, total_vat, total_including_tax, created_at
            FROM invoices
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _invoice_response(row)


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(current_user: UserResponse = Depends(get_current_user)) -> list[InvoiceResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, client_id, invoice_number, issue_date, due_date, status,
                   total_excluding_tax, total_vat, total_including_tax, created_at
            FROM invoices
            WHERE user_id = ?
            ORDER BY id
            """,
            (current_user.id,),
        ).fetchall()
    return [_invoice_response(row) for row in rows]
