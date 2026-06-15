from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

from app.auth import UserPublic, get_current_user
from app.database import connect
from app.financial import FinancialLineInput, calculate_invoice_totals, money

router = APIRouter(prefix="/invoices", tags=["invoices"])
DEFAULT_INVOICE_PREFIX = "F"
InvoiceStatus = Literal["draft", "issued", "paid", "cancelled"]


class InvoiceLineCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price_excluding_tax: Decimal = Field(ge=0)
    vat_rate: Decimal = Field(ge=0)

    @field_validator("description", mode="before")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return str(value).strip()


class InvoiceCreate(BaseModel):
    client_id: int
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    currency: str = "EUR"
    legal_notice: str | None = None
    lines: list[InvoiceLineCreate] = Field(default_factory=list)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        currency = str(value).strip().upper()
        if len(currency) != 3:
            raise ValueError("Currency must be an ISO 4217 code")
        return currency

    @field_validator("legal_notice", mode="before")
    @classmethod
    def strip_legal_notice(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class InvoiceUpdate(BaseModel):
    client_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    status: InvoiceStatus | None = None
    currency: str | None = None
    legal_notice: str | None = None
    lines: list[InvoiceLineCreate] | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return InvoiceCreate.normalize_currency(value)

    @field_validator("legal_notice", mode="before")
    @classmethod
    def strip_legal_notice(cls, value: str | None) -> str | None:
        return InvoiceCreate.strip_legal_notice(value)


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


def _decimal_to_db(value: Decimal) -> str:
    return str(money(value))


def _assert_client_belongs_to_user(connection: sqlite3.Connection, user_id: int, client_id: int) -> None:
    client = connection.execute(
        "SELECT id FROM clients WHERE id = ? AND user_id = ?",
        (client_id, user_id),
    ).fetchone()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")


def _get_invoice_row(connection: sqlite3.Connection, user_id: int, invoice_id: int) -> sqlite3.Row:
    invoice = connection.execute(
        "SELECT * FROM invoices WHERE id = ? AND user_id = ?",
        (invoice_id, user_id),
    ).fetchone()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _calculate_totals(lines: list[InvoiceLineCreate]):
    return calculate_invoice_totals(
        [
            FinancialLineInput(
                description=line.description,
                quantity=line.quantity,
                unit_price_excluding_tax=line.unit_price_excluding_tax,
                vat_rate=line.vat_rate,
            )
            for line in lines
        ]
    )


def _replace_invoice_lines(
    connection: sqlite3.Connection,
    invoice_id: int,
    lines: list[InvoiceLineCreate],
) -> tuple[str, str, str]:
    connection.execute("DELETE FROM invoice_lines WHERE invoice_id = ?", (invoice_id,))
    totals = _calculate_totals(lines)
    for index, line_total in enumerate(totals.lines, start=1):
        line = line_total.line
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
                _decimal_to_db(line_total.excluding_tax),
                _decimal_to_db(line_total.tax),
                _decimal_to_db(line_total.including_tax),
            ),
        )
    return (_decimal_to_db(totals.excluding_tax), _decimal_to_db(totals.tax), _decimal_to_db(totals.including_tax))


def create_invoice_for_user(user_id: int, payload: InvoiceCreate) -> InvoicePublic:
    with connect() as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            _assert_client_belongs_to_user(connection, user_id, payload.client_id)
            invoice_number = _next_invoice_number(connection, user_id)
            totals = _calculate_totals(payload.lines)
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
                    _decimal_to_db(totals.excluding_tax),
                    _decimal_to_db(totals.tax),
                    _decimal_to_db(totals.including_tax),
                    payload.legal_notice,
                ),
            ).lastrowid
            total_excluding_tax, total_tax, total_including_tax = _replace_invoice_lines(
                connection, invoice_id, payload.lines
            )
            connection.execute(
                """
                UPDATE invoices
                SET total_excluding_tax = ?, total_tax = ?, total_including_tax = ?
                WHERE id = ?
                """,
                (total_excluding_tax, total_tax, total_including_tax, invoice_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        return get_invoice_for_user(connection, user_id, invoice_id)


def get_invoice_for_user(connection: sqlite3.Connection, user_id: int, invoice_id: int) -> InvoicePublic:
    invoice = _get_invoice_row(connection, user_id, invoice_id)
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
        total_excluding_tax=money(Decimal(str(invoice["total_excluding_tax"]))),
        total_tax=money(Decimal(str(invoice["total_tax"]))),
        total_including_tax=money(Decimal(str(invoice["total_including_tax"]))),
        legal_notice=invoice["legal_notice"],
        lines=[
            InvoiceLinePublic(
                id=row["id"],
                line_order=row["line_order"],
                description=row["description"],
                quantity=Decimal(str(row["quantity"])),
                unit_price_excluding_tax=money(Decimal(str(row["unit_price_excluding_tax"]))),
                vat_rate=Decimal(str(row["vat_rate"])),
                line_total_excluding_tax=money(Decimal(str(row["line_total_excluding_tax"]))),
                line_total_tax=money(Decimal(str(row["line_total_tax"]))),
                line_total_including_tax=money(Decimal(str(row["line_total_including_tax"]))),
            )
            for row in line_rows
        ],
    )



def update_invoice_for_user(user_id: int, invoice_id: int, payload: InvoiceUpdate) -> InvoicePublic:
    with connect() as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = _get_invoice_row(connection, user_id, invoice_id)
            values = {
                "client_id": existing["client_id"],
                "issue_date": date.fromisoformat(existing["issue_date"]),
                "due_date": date.fromisoformat(existing["due_date"]) if existing["due_date"] else None,
                "status": existing["status"],
                "currency": existing["currency"],
                "legal_notice": existing["legal_notice"],
            }
            values.update(payload.model_dump(exclude_unset=True))
            _assert_client_belongs_to_user(connection, user_id, values["client_id"])

            if payload.lines is not None:
                total_excluding_tax, total_tax, total_including_tax = _replace_invoice_lines(
                    connection, invoice_id, payload.lines
                )
            else:
                total_excluding_tax = str(existing["total_excluding_tax"])
                total_tax = str(existing["total_tax"])
                total_including_tax = str(existing["total_including_tax"])

            connection.execute(
                """
                UPDATE invoices
                SET client_id = ?, issue_date = ?, due_date = ?, status = ?, currency = ?,
                    total_excluding_tax = ?, total_tax = ?, total_including_tax = ?,
                    legal_notice = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (
                    values["client_id"],
                    values["issue_date"].isoformat(),
                    values["due_date"].isoformat() if values["due_date"] else None,
                    values["status"],
                    values["currency"],
                    total_excluding_tax,
                    total_tax,
                    total_including_tax,
                    values["legal_notice"],
                    invoice_id,
                    user_id,
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        return get_invoice_for_user(connection, user_id, invoice_id)


@router.get("", response_model=list[InvoicePublic])
def list_invoices(current_user: UserPublic = Depends(get_current_user)) -> list[InvoicePublic]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id FROM invoices
            WHERE user_id = ?
            ORDER BY issue_date DESC, id DESC
            """,
            (current_user.id,),
        ).fetchall()
        return [get_invoice_for_user(connection, current_user.id, row["id"]) for row in rows]


@router.get("/{invoice_id}", response_model=InvoicePublic)
def read_invoice(invoice_id: int, current_user: UserPublic = Depends(get_current_user)) -> InvoicePublic:
    with connect() as connection:
        return get_invoice_for_user(connection, current_user.id, invoice_id)


@router.patch("/{invoice_id}", response_model=InvoicePublic)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    current_user: UserPublic = Depends(get_current_user),
) -> InvoicePublic:
    return update_invoice_for_user(current_user.id, invoice_id, payload)


@router.put("/{invoice_id}", response_model=InvoicePublic)
def replace_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    current_user: UserPublic = Depends(get_current_user),
) -> InvoicePublic:
    return update_invoice_for_user(current_user.id, invoice_id, payload)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_invoice(invoice_id: int, current_user: UserPublic = Depends(get_current_user)) -> Response:
    with connect() as connection:
        _get_invoice_row(connection, current_user.id, invoice_id)
        connection.execute("DELETE FROM invoices WHERE id = ? AND user_id = ?", (invoice_id, current_user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=InvoicePublic, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, current_user: UserPublic = Depends(get_current_user)) -> InvoicePublic:
    return create_invoice_for_user(current_user.id, payload)
