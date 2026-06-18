from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from textwrap import wrap


@dataclass(frozen=True)
class PdfInvoiceLine:
    description: str
    quantity: float
    unit_price: float
    tax_rate: float
    total_excluding_tax: float
    total_tax: float
    total_including_tax: float


@dataclass(frozen=True)
class PdfInvoice:
    issuer_name: str
    issuer_email: str
    client_name: str
    client_email: str | None
    client_address: str
    invoice_number: str
    issue_date: str
    due_date: str | None
    currency: str
    lines: list[PdfInvoiceLine]
    total_excluding_tax: float
    total_tax: float
    total_including_tax: float


def format_amount(value: float, currency: str = "EUR") -> str:
    return f"{value:.2f} {currency}"


def format_number(value: float) -> str:
    return f"{value:g}"


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def normalize_pdf_text(value: str) -> str:
    return value.encode("latin-1", errors="replace").decode("latin-1")


def build_invoice_pdf(invoice: PdfInvoice) -> bytes:
    lines = [
        "FacNor - Facture normalisee France",
        f"Emetteur: {invoice.issuer_name}",
        f"Email emetteur: {invoice.issuer_email}",
        f"Client: {invoice.client_name}",
    ]
    if invoice.client_email:
        lines.append(f"Email client: {invoice.client_email}")
    lines.extend(
        [
            f"Adresse client: {invoice.client_address}",
            f"Numero: {invoice.invoice_number}",
            f"Date: {invoice.issue_date}",
        ],
    )
    if invoice.due_date:
        lines.append(f"Echeance: {invoice.due_date}")

    lines.extend(
        [
            "",
            "Detail des lignes:",
            "Description | Qte | Prix HT | TVA | Total HT | TVA | TTC",
        ]
    )
    for line in invoice.lines:
        description_parts = wrap(line.description, width=32) or [""]
        first_description, extra_descriptions = (
            description_parts[0],
            description_parts[1:],
        )
        lines.append(
            " | ".join(
                [
                    first_description,
                    format_number(line.quantity),
                    format_amount(line.unit_price, invoice.currency),
                    f"{format_number(line.tax_rate)}%",
                    format_amount(line.total_excluding_tax, invoice.currency),
                    format_amount(line.total_tax, invoice.currency),
                    format_amount(line.total_including_tax, invoice.currency),
                ],
            ),
        )
        lines.extend(f"  {part}" for part in extra_descriptions)

    tax_rates = sorted({line.tax_rate for line in invoice.lines})
    lines.extend(
        [
            "",
            "Taux de TVA: "
            + ", ".join(f"{format_number(rate)}%" for rate in tax_rates),
            f"Total HT: {format_amount(invoice.total_excluding_tax, invoice.currency)}",
            f"Total TVA: {format_amount(invoice.total_tax, invoice.currency)}",
            f"Total TTC: {format_amount(invoice.total_including_tax, invoice.currency)}",
        ],
    )
    return build_simple_pdf(lines)


def build_simple_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index:
            content_lines.append("T*")
        content_lines.append(f"({escape_pdf_text(normalize_pdf_text(line))}) Tj")
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode("ascii")
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]

    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{index} 0 obj\n".encode("ascii"))
        buffer.write(obj)
        buffer.write(b"\nendobj\n")

    xref_offset = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        ),
    )
    return buffer.getvalue()
