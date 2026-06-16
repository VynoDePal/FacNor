from __future__ import annotations

from decimal import Decimal
import sqlite3
from typing import Iterable


def generate_invoice_pdf(connection: sqlite3.Connection, invoice_id: int) -> bytes | None:
    invoice = connection.execute(
        """
        SELECT
            invoices.*,
            users.email AS issuer_email,
            users.full_name AS issuer_full_name,
            users.company_name AS issuer_company_name,
            users.siren AS issuer_siren,
            users.vat_number AS issuer_vat_number,
            clients.name AS client_name,
            clients.email AS client_email,
            clients.address AS client_address,
            clients.postal_code AS client_postal_code,
            clients.city AS client_city,
            clients.country AS client_country,
            clients.siren AS client_siren,
            clients.vat_number AS client_vat_number
        FROM invoices
        JOIN users ON users.id = invoices.user_id
        JOIN clients ON clients.id = invoices.client_id
        WHERE invoices.id = ?
        """,
        (invoice_id,),
    ).fetchone()
    if invoice is None:
        return None

    lines = connection.execute(
        """
        SELECT * FROM invoice_lines
        WHERE invoice_id = ?
        ORDER BY line_order
        """,
        (invoice_id,),
    ).fetchall()

    return _render_pdf(_invoice_text_lines(dict(invoice), [dict(line) for line in lines]))


def _invoice_text_lines(invoice: dict, lines: list[dict]) -> list[str]:
    issuer_name = invoice.get("issuer_company_name") or invoice.get("issuer_full_name") or invoice.get("issuer_email")
    text = [
        f"Facture {invoice['invoice_number']}",
        "",
        "Emetteur",
        str(issuer_name),
        f"Email : {invoice.get('issuer_email') or 'Non renseigne'}",
        f"SIREN : {invoice.get('issuer_siren') or 'Non renseigne'}",
        f"TVA intracommunautaire : {invoice.get('issuer_vat_number') or 'Non renseigne'}",
        "",
        "Client",
        str(invoice["client_name"]),
        f"Email : {invoice.get('client_email') or 'Non renseigne'}",
        str(invoice["client_address"]),
        f"{invoice['client_postal_code']} {invoice['client_city']} - {invoice['client_country']}",
        f"SIREN : {invoice.get('client_siren') or 'Non renseigne'}",
        f"TVA intracommunautaire : {invoice.get('client_vat_number') or 'Non renseigne'}",
        "",
        "Dates",
        f"Date d'emission : {invoice['issue_date']}",
        f"Date d'echeance : {invoice.get('due_date') or 'Non renseignee'}",
        f"Statut : {invoice['status']}",
        "",
        "Details des lignes",
        "Description | Quantite | Prix unitaire HT | TVA | Total HT | Total TVA | Total TTC",
    ]

    for line in lines:
        text.append(
            " | ".join(
                [
                    str(line["description"]),
                    _format_decimal(line["quantity"]),
                    _format_money(line["unit_price_excluding_tax"], invoice["currency"]),
                    f"{_format_decimal(line['vat_rate'])} %",
                    _format_money(line["total_excluding_tax"], invoice["currency"]),
                    _format_money(line["total_tax"], invoice["currency"]),
                    _format_money(line["total_including_tax"], invoice["currency"]),
                ]
            )
        )

    text.extend(
        [
            "",
            "Totaux",
            f"Total HT : {_format_money(invoice['total_excluding_tax'], invoice['currency'])}",
            f"Total TVA : {_format_money(invoice['total_tax'], invoice['currency'])}",
            f"Total TTC : {_format_money(invoice['total_including_tax'], invoice['currency'])}",
            "",
            "Mentions legales",
            "Facture emise par FacNor conformement aux obligations de facturation applicables en France.",
            "Montants exprimes en centimes dans la base et presentes en euros sur ce document.",
        ]
    )
    return text


def _format_money(amount_cents: int, currency: str) -> str:
    amount = Decimal(int(amount_cents)) / Decimal(100)
    return f"{amount:.2f} {currency}"


def _format_decimal(value: object) -> str:
    decimal = Decimal(str(value))
    return format(decimal.normalize(), "f")


def _render_pdf(lines: Iterable[str]) -> bytes:
    line_list = list(lines)
    title = line_list[0] if line_list else "Facture"
    commands = ["BT", "/F1 16 Tf", "1 0 0 1 50 820 Tm", f"({_escape_pdf_text(title)}) Tj", "ET"]

    commands.extend(["BT", "/F1 10 Tf"])
    y = 800
    for line in line_list[1:]:
        if y < 50:
            commands.append(f"1 0 0 1 50 {y} Tm")
            commands.append(f"({_escape_pdf_text('Suite sur export numerique')}) Tj")
            break
        commands.append(f"1 0 0 1 50 {y} Tm")
        commands.append(f"({_escape_pdf_text(line[:120])}) Tj")
        y -= 14
    commands.append("ET")

    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\r", " ").replace("\n", " ")
