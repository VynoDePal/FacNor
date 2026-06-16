from __future__ import annotations

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
            "SELECT next_number FROM invoice_sequences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if sequence_row is None:
            connection.execute(
                "INSERT INTO invoice_sequences (user_id, next_number) VALUES (?, 1)",
                (user_id,),
            )
            sequence_number = 1
        else:
            sequence_number = int(sequence_row["next_number"])

        invoice_number = f"FAC-{sequence_number:06d}"
        totals = [_line_totals(line) for line in lines]
        total_excluding_tax = sum(total[0] for total in totals)
        total_tax = sum(total[1] for total in totals)
        total_including_tax = total_excluding_tax + total_tax

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

        for index, (line, (line_total_ht, line_total_tax)) in enumerate(zip(lines, totals), start=1):
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
                    line_total_ht + line_total_tax,
                ),
            )

        connection.execute(
            "UPDATE invoice_sequences SET next_number = ? WHERE user_id = ?",
            (sequence_number + 1, user_id),
        )

    return dict(
        connection.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    )


def _line_totals(line: Mapping[str, object]) -> tuple[int, int]:
    quantity = float(line["quantity"])
    unit_price = int(line["unit_price_excluding_tax"])
    vat_rate = float(line["vat_rate"])
    total_excluding_tax = round(quantity * unit_price)
    total_tax = round(total_excluding_tax * vat_rate / 100)
    return total_excluding_tax, total_tax
