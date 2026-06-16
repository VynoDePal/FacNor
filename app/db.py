from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import os
import sqlite3
from pathlib import Path
from typing import Mapping, Sequence

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT_DIR / "schema.sql"
DEFAULT_DATABASE_URL = f"sqlite:///{ROOT_DIR / 'facnor.db'}"


def database_path(database_url: str | None = None) -> str:
    url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if url == "sqlite:///:memory:":
        return ":memory:"
    if url.startswith("sqlite:///"):
        return url.removeprefix("sqlite:///")
    return url


def connect(database_url: str | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path(database_url), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection | None = None) -> sqlite3.Connection:
    owns_connection = connection is None
    connection = connection or connect()
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        connection.executescript(schema_file.read())
    if owns_connection:
        connection.commit()
    return connection


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return None if row is None else dict(row)


def create_invoice(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    client_id: int,
    lines: Sequence[Mapping[str, object]],
    issue_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    if not lines:
        raise ValueError("An invoice requires at least one line")

    with connection:
        sequence_row = connection.execute(
            """
            INSERT INTO invoice_sequences (user_id, next_number)
            VALUES (?, 2)
            ON CONFLICT(user_id) DO UPDATE SET next_number = next_number + 1
            RETURNING next_number - 1 AS sequence_number
            """,
            (user_id,),
        ).fetchone()
        sequence_number = int(sequence_row["sequence_number"])

        invoice_number = f"FAC-{sequence_number:06d}"
        totals = [_line_totals(line) for line in lines]
        total_excluding_tax = sum(total[0] for total in totals)
        total_tax = sum(total[1] for total in totals)
        total_including_tax = sum(total[2] for total in totals)

        cursor = connection.execute(
            """
            INSERT INTO invoices (
                user_id, client_id, sequence_number, invoice_number, issue_date, due_date,
                total_excluding_tax, total_tax, total_including_tax
            )
            VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_DATE), ?, ?, ?, ?)
            """,
            (
                user_id,
                client_id,
                sequence_number,
                invoice_number,
                issue_date,
                due_date,
                total_excluding_tax,
                total_tax,
                total_including_tax,
            ),
        )
        invoice_id = int(cursor.lastrowid)

        for index, (line, (line_total_ht, line_total_tax, line_total_ttc)) in enumerate(zip(lines, totals), start=1):
            connection.execute(
                """
                INSERT INTO invoice_lines (
                    invoice_id, line_order, description, quantity, unit_price_excluding_tax,
                    vat_rate, total_excluding_tax, total_tax, total_including_tax
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    index,
                    str(line["description"]),
                    line["quantity"],
                    int(line["unit_price_excluding_tax"]),
                    line["vat_rate"],
                    line_total_ht,
                    line_total_tax,
                    line_total_ttc,
                ),
            )

    return get_invoice(connection, invoice_id)


def get_invoice(connection: sqlite3.Connection, invoice_id: int) -> dict | None:
    invoice = row_to_dict(connection.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
    if invoice is None:
        return None
    invoice["lines"] = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM invoice_lines WHERE invoice_id = ? ORDER BY line_order",
            (invoice_id,),
        ).fetchall()
    ]
    return invoice


def update_invoice(
    connection: sqlite3.Connection,
    invoice_id: int,
    *,
    client_id: int | None = None,
    issue_date: str | None = None,
    due_date: str | None = None,
    status: str | None = None,
    lines: Sequence[Mapping[str, object]] | None = None,
) -> dict | None:
    with connection:
        if client_id is not None or issue_date is not None or due_date is not None or status is not None:
            updates = []
            values: list[object] = []
            for field, value in (
                ("client_id", client_id),
                ("issue_date", issue_date),
                ("due_date", due_date),
                ("status", status),
            ):
                if value is not None:
                    updates.append(f"{field} = ?")
                    values.append(value)
            if updates:
                connection.execute(
                    f"UPDATE invoices SET {', '.join(updates)} WHERE id = ?",
                    (*values, invoice_id),
                )

        if lines is not None:
            if not lines:
                raise ValueError("An invoice requires at least one line")
            totals = [_line_totals(line) for line in lines]
            connection.execute("DELETE FROM invoice_lines WHERE invoice_id = ?", (invoice_id,))
            for index, (line, (line_total_ht, line_total_tax, line_total_ttc)) in enumerate(zip(lines, totals), start=1):
                connection.execute(
                    """
                    INSERT INTO invoice_lines (
                        invoice_id, line_order, description, quantity, unit_price_excluding_tax,
                        vat_rate, total_excluding_tax, total_tax, total_including_tax
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        index,
                        str(line["description"]),
                        line["quantity"],
                        int(line["unit_price_excluding_tax"]),
                        line["vat_rate"],
                        line_total_ht,
                        line_total_tax,
                        line_total_ttc,
                    ),
                )
            connection.execute(
                """
                UPDATE invoices
                SET total_excluding_tax = ?, total_tax = ?, total_including_tax = ?
                WHERE id = ?
                """,
                (
                    sum(total[0] for total in totals),
                    sum(total[1] for total in totals),
                    sum(total[2] for total in totals),
                    invoice_id,
                ),
            )

    return get_invoice(connection, invoice_id)



def _line_totals(line: Mapping[str, object]) -> tuple[int, int, int]:
    quantity = Decimal(str(line["quantity"]))
    unit_price = Decimal(int(line["unit_price_excluding_tax"]))
    vat_rate = Decimal(str(line["vat_rate"]))
    total_excluding_tax = int((quantity * unit_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total_tax = int((Decimal(total_excluding_tax) * vat_rate / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return total_excluding_tax, total_tax, total_excluding_tax + total_tax
