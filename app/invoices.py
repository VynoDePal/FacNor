from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.auth import UserResponse, get_current_user
from app.database import get_connection
from app.pdf_export import ClientPdfData, generate_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["invoices"])

InvoiceStatus = Literal["draft", "issued", "paid", "cancelled"]
MONEY_QUANTUM = Decimal("0.01")


class InvoiceItemBase(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit_price_excluding_tax: Decimal = Field(ge=0)
    vat_rate: Decimal = Field(ge=0)


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(InvoiceItemBase):
    id: int
    line_total_excluding_tax: Decimal
    line_total_vat: Decimal
    line_total_including_tax: Decimal
    created_at: str


class InvoiceCreate(BaseModel):
    client_id: int
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    status: InvoiceStatus = "draft"
    items: list[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceUpdate(BaseModel):
    client_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    status: InvoiceStatus | None = None
    items: list[InvoiceItemCreate] | None = None


class InvoiceResponse(BaseModel):
    id: int
    user_id: int
    client_id: int
    invoice_number: str
    issue_date: str
    due_date: str | None = None
    status: InvoiceStatus
    total_excluding_tax: Decimal
    total_vat: Decimal
    total_including_tax: Decimal
    created_at: str
    items: list[InvoiceItemResponse] = Field(default_factory=list)


INVOICE_NUMBER_PREFIX = "FAC"
INVOICE_NUMBER_WIDTH = 6
INVOICE_SEQUENCE_NAME = "global_invoice_number"


def format_invoice_number(sequence_number: int) -> str:
    if sequence_number < 1:
        raise ValueError("Le numéro de séquence doit être positif.")
    return f"{INVOICE_NUMBER_PREFIX}-{sequence_number:0{INVOICE_NUMBER_WIDTH}d}"


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _model_dump(model: BaseModel) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _decimal_from_db(value, *, min_decimal_places: int = 0) -> Decimal:
    decimal_value = Decimal(str(value))
    if min_decimal_places and decimal_value == decimal_value.to_integral_value():
        return decimal_value.quantize(Decimal("1." + ("0" * min_decimal_places)))
    return decimal_value


def _invoice_item_response(row) -> InvoiceItemResponse:
    return InvoiceItemResponse(
        id=row["id"],
        description=row["description"],
        quantity=Decimal(str(row["quantity"])),
        unit_price_excluding_tax=Decimal(str(row["unit_price_excluding_tax"])),
        vat_rate=Decimal(str(row["vat_rate"])),
        line_total_excluding_tax=_decimal_from_db(row["line_total_excluding_tax"], min_decimal_places=1),
        line_total_vat=_decimal_from_db(row["line_total_vat"], min_decimal_places=1),
        line_total_including_tax=_decimal_from_db(row["line_total_including_tax"], min_decimal_places=1),
        created_at=row["created_at"],
    )


def _invoice_response(row, items: list[InvoiceItemResponse] | None = None) -> InvoiceResponse:
    return InvoiceResponse(
        id=row["id"],
        user_id=row["user_id"],
        client_id=row["client_id"],
        invoice_number=row["invoice_number"],
        issue_date=row["issue_date"],
        due_date=row["due_date"],
        status=row["status"],
        total_excluding_tax=_decimal_from_db(row["total_excluding_tax"], min_decimal_places=1),
        total_vat=_decimal_from_db(row["total_vat"], min_decimal_places=1),
        total_including_tax=_decimal_from_db(row["total_including_tax"], min_decimal_places=1),
        created_at=row["created_at"],
        items=items or [],
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


def _get_invoice_row(connection, invoice_id: int, user_id: int):
    row = connection.execute(
        """
        SELECT id, user_id, client_id, invoice_number, issue_date, due_date, status,
               total_excluding_tax, total_vat, total_including_tax, created_at
        FROM invoices
        WHERE id = ? AND user_id = ?
        """,
        (invoice_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable.")
    return row



def _get_invoice_client_pdf_data(connection, invoice_id: int, user_id: int) -> ClientPdfData:
    row = connection.execute(
        """
        SELECT clients.name, clients.client_type, clients.email, clients.address,
               clients.siren, clients.vat_number
        FROM invoices
        JOIN clients ON clients.id = invoices.client_id
        WHERE invoices.id = ? AND invoices.user_id = ?
        """,
        (invoice_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable.")
    return ClientPdfData(
        name=row["name"],
        client_type=row["client_type"],
        email=row["email"],
        address=row["address"],
        siren=row["siren"],
        vat_number=row["vat_number"],
    )


def _get_invoice_items(connection, invoice_id: int) -> list[InvoiceItemResponse]:
    rows = connection.execute(
        """
        SELECT id, description, quantity, unit_price_excluding_tax, vat_rate,
               line_total_excluding_tax, line_total_vat, line_total_including_tax, created_at
        FROM invoice_items
        WHERE invoice_id = ?
        ORDER BY id
        """,
        (invoice_id,),
    ).fetchall()
    return [_invoice_item_response(row) for row in rows]


def _replace_invoice_items(connection, invoice_id: int, items: list[InvoiceItemCreate]) -> tuple[Decimal, Decimal, Decimal]:
    connection.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    total_excluding_tax = Decimal("0.00")
    total_vat = Decimal("0.00")

    for item in items:
        data = _model_dump(item)
        quantity = Decimal(str(data["quantity"]))
        unit_price = Decimal(str(data["unit_price_excluding_tax"]))
        vat_rate = Decimal(str(data["vat_rate"]))
        line_total_excluding_tax = _money(quantity * unit_price)
        line_total_vat = _money(line_total_excluding_tax * vat_rate / Decimal("100"))
        line_total_including_tax = _money(line_total_excluding_tax + line_total_vat)
        total_excluding_tax += line_total_excluding_tax
        total_vat += line_total_vat
        connection.execute(
            """
            INSERT INTO invoice_items (
                invoice_id, description, quantity, unit_price_excluding_tax, vat_rate,
                line_total_excluding_tax, line_total_vat, line_total_including_tax
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                data["description"],
                str(quantity),
                str(unit_price),
                str(vat_rate),
                str(line_total_excluding_tax),
                str(line_total_vat),
                str(line_total_including_tax),
            ),
        )

    total_excluding_tax = _money(total_excluding_tax)
    total_vat = _money(total_vat)
    total_including_tax = _money(total_excluding_tax + total_vat)
    connection.execute(
        """
        UPDATE invoices
        SET total_excluding_tax = ?, total_vat = ?, total_including_tax = ?
        WHERE id = ?
        """,
        (str(total_excluding_tax), str(total_vat), str(total_including_tax), invoice_id),
    )
    return total_excluding_tax, total_vat, total_including_tax


def _invoice_with_items(connection, invoice_id: int, user_id: int) -> InvoiceResponse:
    row = _get_invoice_row(connection, invoice_id, user_id)
    return _invoice_response(row, _get_invoice_items(connection, invoice_id))


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
            INSERT INTO invoices (user_id, client_id, invoice_number, issue_date, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                payload.client_id,
                invoice_number,
                payload.issue_date.isoformat(),
                payload.due_date.isoformat() if payload.due_date else None,
                payload.status,
            ),
        )
        invoice_id = cursor.lastrowid
        _replace_invoice_items(connection, invoice_id, payload.items)
        return _invoice_with_items(connection, invoice_id, current_user.id)


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(
    q: str | None = None,
    status: InvoiceStatus | None = None,
    client_id: int | None = None,
    issue_date_from: date | None = None,
    issue_date_to: date | None = None,
    current_user: UserResponse = Depends(get_current_user),
) -> list[InvoiceResponse]:
    filters = ["invoices.user_id = ?"]
    parameters: list[object] = [current_user.id]

    search_query = q.strip().lower() if q else ""
    if search_query:
        search = f"%{search_query}%"
        filters.append("(LOWER(invoices.invoice_number) LIKE ? OR LOWER(clients.name) LIKE ?)")
        parameters.extend([search, search])
    if status:
        filters.append("invoices.status = ?")
        parameters.append(status)
    if client_id is not None:
        filters.append("invoices.client_id = ?")
        parameters.append(client_id)
    if issue_date_from is not None:
        filters.append("invoices.issue_date >= ?")
        parameters.append(issue_date_from.isoformat())
    if issue_date_to is not None:
        filters.append("invoices.issue_date <= ?")
        parameters.append(issue_date_to.isoformat())

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT invoices.id, invoices.user_id, invoices.client_id, invoices.invoice_number,
                   invoices.issue_date, invoices.due_date, invoices.status,
                   invoices.total_excluding_tax, invoices.total_vat,
                   invoices.total_including_tax, invoices.created_at
            FROM invoices
            JOIN clients ON clients.id = invoices.client_id
            WHERE {' AND '.join(filters)}
            ORDER BY invoices.id
            """,
            tuple(parameters),
        ).fetchall()
        return [_invoice_response(row, _get_invoice_items(connection, row["id"])) for row in rows]


@router.get("/{invoice_id}/pdf", response_class=Response)
def export_invoice_pdf(
    invoice_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        invoice = _invoice_with_items(connection, invoice_id, current_user.id)
        client = _get_invoice_client_pdf_data(connection, invoice_id, current_user.id)

    pdf_content = generate_invoice_pdf(invoice, client, current_user)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"',
        },
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> InvoiceResponse:
    with get_connection() as connection:
        return _invoice_with_items(connection, invoice_id, current_user.id)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> InvoiceResponse:
    data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = _get_invoice_row(connection, invoice_id, current_user.id)
        client_id = data.get("client_id", current["client_id"])
        _ensure_client_belongs_to_user(connection, client_id, current_user.id)
        issue_date = data.get("issue_date", current["issue_date"])
        due_date = data.get("due_date", current["due_date"])
        connection.execute(
            """
            UPDATE invoices
            SET client_id = ?, issue_date = ?, due_date = ?, status = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                client_id,
                issue_date.isoformat() if isinstance(issue_date, date) else issue_date,
                due_date.isoformat() if isinstance(due_date, date) else due_date,
                data.get("status", current["status"]),
                invoice_id,
                current_user.id,
            ),
        )
        if "items" in data:
            _replace_invoice_items(connection, invoice_id, payload.items or [])
        return _invoice_with_items(connection, invoice_id, current_user.id)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    with get_connection() as connection:
        _get_invoice_row(connection, invoice_id, current_user.id)
        connection.execute("DELETE FROM invoices WHERE id = ? AND user_id = ?", (invoice_id, current_user.id))
