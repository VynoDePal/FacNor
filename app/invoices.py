from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import UserPublic, get_current_user
from app.database import connect

router = APIRouter(prefix="/invoices", tags=["invoices"])
DEFAULT_INVOICE_PREFIX = "F"


class InvoiceLineCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price_excluding_tax: Decimal = Field(ge=0)
    vat_rate: Decimal = Field(ge=0)


class InvoiceCreate(BaseModel):
    client_id: int
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    currency: str = "EUR"
    legal_notice: str | None = None
    lines: list[InvoiceLineCreate] = Field(default_factory=list)


class InvoiceLinePublic(BaseModel):
    id: int
    line_order: int
    description: str
    quantity: Decimal
    unit_price_excluding_tax: Decimal
    vat_rate: Decimal
    line_total_excluding_tax: Decimal
    line_total_tax: Decimal
    line_total_including_tax: Decimal


class InvoicePublic(BaseModel):
    id: int
    user_id: int
    client_id: int
    invoice_number: str
    issue_date: date
    due_date: date | None = None
    status: str
    currency: str
    total_excluding_tax: Decimal
    total_tax: Decimal
    total_including_tax: Decimal
    legal_notice: str | None = None
    lines: list[InvoiceLinePublic] = Field(default_factory=list)


def _format_invoice_number(prefix: str, number: int) -> str:
    return f"{prefix}-{number:03d}"


def _next_invoice_number(connection: sqlite3.Connection, user_id: int, prefix: str = DEFAULT_INVOICE_PREFIX) -> str:
    row = connection.execute(
        "SELECT last_number FROM invoice_sequences WHERE user_id = ? AND prefix = ?",
        (user_id, prefix),
    ).fetchone()
    if row is None:
        last_number = 0
        connection.execute(
            "INSERT INTO invoice_sequences (user_id, prefix, last_number) VALUES (?, ?, ?)",
            (user_id, prefix, last_number),
        )
    else:
        last_number = int(row["last_number"])

    next_number = last_number + 1
    connection.execute(
        """
        UPDATE invoice_sequences
        SET last_number = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND prefix = ?
        """,
        (next_number, user_id, prefix),
    )
    return _format_invoice_number(prefix, next_number)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _decimal_to_db(value: Decimal) -> str:
    return str(_money(value))


def create_invoice_for_user(user_id: int, payload: InvoiceCreate) -> InvoicePublic:
    with connect() as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            client = connection.execute(
                "SELECT id FROM clients WHERE id = ? AND user_id = ?",
                (payload.client_id, user_id),
            ).fetchone()
            if client is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

            line_totals: list[tuple[InvoiceLineCreate, Decimal, Decimal, Decimal]] = []
            total_excluding_tax = Decimal("0.00")
            total_tax = Decimal("0.00")
            total_including_tax = Decimal("0.00")
            for line in payload.lines:
                excluding_tax = line.quantity * line.unit_price_excluding_tax
                tax = excluding_tax * line.vat_rate / Decimal("100")
                including_tax = excluding_tax + tax
                line_totals.append((line, excluding_tax, tax, including_tax))
                total_excluding_tax += excluding_tax
                total_tax += tax
                total_including_tax += including_tax

            invoice_number = _next_invoice_number(connection, user_id)
            invoice_id = connection.execute(
                """
                INSERT INTO invoices (
                    user_id, client_id, invoice_number, issue_date, due_date, currency,
                    total_excluding_tax, total_tax, total_including_tax, legal_notice
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    payload.client_id,
                    invoice_number,
                    payload.issue_date.isoformat(),
                    payload.due_date.isoformat() if payload.due_date else None,
                    payload.currency,
                    _decimal_to_db(total_excluding_tax),
                    _decimal_to_db(total_tax),
                    _decimal_to_db(total_including_tax),
                    payload.legal_notice,
                ),
            ).lastrowid

            for index, (line, excluding_tax, tax, including_tax) in enumerate(line_totals, start=1):
                connection.execute(
                    """
                    INSERT INTO invoice_lines (
                        invoice_id, line_order, description, quantity, unit_price_excluding_tax,
                        vat_rate, line_total_excluding_tax, line_total_tax, line_total_including_tax
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        index,
                        line.description,
                        str(line.quantity),
                        str(line.unit_price_excluding_tax),
                        str(line.vat_rate),
                        _decimal_to_db(excluding_tax),
                        _decimal_to_db(tax),
                        _decimal_to_db(including_tax),
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        return get_invoice_for_user(connection, user_id, invoice_id)


def get_invoice_for_user(connection: sqlite3.Connection, user_id: int, invoice_id: int) -> InvoicePublic:
    invoice = connection.execute(
        "SELECT * FROM invoices WHERE id = ? AND user_id = ?",
        (invoice_id, user_id),
    ).fetchone()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    line_rows = connection.execute(
        "SELECT * FROM invoice_lines WHERE invoice_id = ? ORDER BY line_order",
        (invoice_id,),
    ).fetchall()
    return InvoicePublic(
        id=invoice["id"],
        user_id=invoice["user_id"],
        client_id=invoice["client_id"],
        invoice_number=invoice["invoice_number"],
        issue_date=date.fromisoformat(invoice["issue_date"]),
        due_date=date.fromisoformat(invoice["due_date"]) if invoice["due_date"] else None,
        status=invoice["status"],
        currency=invoice["currency"],
        total_excluding_tax=_money(Decimal(str(invoice["total_excluding_tax"]))),
        total_tax=_money(Decimal(str(invoice["total_tax"]))),
        total_including_tax=_money(Decimal(str(invoice["total_including_tax"]))),
        legal_notice=invoice["legal_notice"],
        lines=[
            InvoiceLinePublic(
                id=row["id"],
                line_order=row["line_order"],
                description=row["description"],
                quantity=Decimal(str(row["quantity"])),
                unit_price_excluding_tax=_money(Decimal(str(row["unit_price_excluding_tax"]))),
                vat_rate=Decimal(str(row["vat_rate"])),
                line_total_excluding_tax=_money(Decimal(str(row["line_total_excluding_tax"]))),
                line_total_tax=_money(Decimal(str(row["line_total_tax"]))),
                line_total_including_tax=_money(Decimal(str(row["line_total_including_tax"]))),
            )
            for row in line_rows
        ],
    )


@router.post("", response_model=InvoicePublic, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, current_user: UserPublic = Depends(get_current_user)) -> InvoicePublic:
    return create_invoice_for_user(current_user.id, payload)
