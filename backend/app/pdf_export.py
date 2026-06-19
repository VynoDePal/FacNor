import unicodedata
from decimal import Decimal

from backend.app.models import Invoice


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 50
LINE_HEIGHT = 14
MAX_LINES_PER_PAGE = (PAGE_HEIGHT - (2 * MARGIN)) // LINE_HEIGHT + 1
TEXT_ENCODING = "latin-1"


def generate_invoice_pdf(invoice: Invoice) -> bytes:
    lines = _invoice_lines(invoice)
    return _build_pdf(lines)


def _invoice_lines(invoice: Invoice) -> list[str]:
    user = invoice.user
    client = invoice.client
    lines = [
        f"Facture {invoice.number}",
        "",
        "Emetteur",
        user.company_name,
        user.address,
        f"SIREN: {_optional(user.siren)}",
        f"TVA intracommunautaire: {_optional(user.vat_number)}",
        "",
        "Client",
        client.name,
        client.address,
        f"SIREN: {_optional(client.siren)}",
        f"TVA intracommunautaire: {_optional(client.vat_number)}",
        "",
        f"Numero de facture: {invoice.number}",
        f"Date d'emission: {invoice.issue_date.isoformat()}",
        f"Date d'echeance: {_optional(invoice.due_date.isoformat() if invoice.due_date else None)}",
        f"Statut: {invoice.status}",
        "",
        "Lignes",
        "Description | Quantite | Prix unitaire HT | TVA | Total HT | Total TVA | Total TTC",
    ]
    for item in invoice.items:
        lines.append(
            " | ".join(
                [
                    item.description,
                    _format_decimal(item.quantity),
                    _format_money(item.unit_price_excluding_tax),
                    f"{_format_decimal(item.vat_rate)}%",
                    _format_money(item.total_excluding_tax),
                    _format_money(item.total_tax),
                    _format_money(item.total_including_tax),
                ]
            )
        )
    lines.extend(
        [
            "",
            f"Total HT: {_format_money(invoice.total_excluding_tax)}",
            f"Total TVA: {_format_money(invoice.total_tax)}",
            f"Total TTC: {_format_money(invoice.total_including_tax)}",
        ]
    )
    return lines


def _build_pdf(lines: list[str]) -> bytes:
    pages = _paginate_lines(_expanded_lines(lines))
    objects = _build_pdf_objects(pages)
    return _serialize_pdf(objects)


def _expanded_lines(lines: list[str]) -> list[str]:
    return [line for raw_line in lines for line in _wrap_line(raw_line)]


def _paginate_lines(lines: list[str]) -> list[list[str]]:
    if not lines:
        return [[""]]
    return [lines[index : index + MAX_LINES_PER_PAGE] for index in range(0, len(lines), MAX_LINES_PER_PAGE)]


def _build_pdf_objects(pages: list[list[str]]) -> list[bytes]:
    page_count = len(pages)
    page_object_ids = [3 + index * 2 for index in range(page_count)]
    content_object_ids = [page_id + 1 for page_id in page_object_ids]
    font_object_id = 3 + page_count * 2

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        _pages_object(page_object_ids),
    ]
    for page_lines, content_id in zip(pages, content_object_ids):
        objects.append(_page_object(content_id, font_object_id))
        objects.append(_content_object(page_lines))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    return objects


def _pages_object(page_object_ids: list[int]) -> bytes:
    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    return f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>".encode("ascii")


def _page_object(content_id: int, font_object_id: int) -> bytes:
    return (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
        f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> /Contents {content_id} 0 R >>"
    ).encode("ascii")


def _content_object(lines: list[str]) -> bytes:
    stream = _page_stream(lines)
    return b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"


def _page_stream(lines: list[str]) -> bytes:
    text_commands = ["BT", "/F1 11 Tf", f"{MARGIN} {PAGE_HEIGHT - MARGIN} Td"]
    for index, line in enumerate(lines):
        if index:
            text_commands.append(f"0 -{LINE_HEIGHT} Td")
        text_commands.append(f"({_escape_pdf_text(line)}) Tj")
    text_commands.append("ET")
    return "\n".join(text_commands).encode(TEXT_ENCODING)


def _serialize_pdf(objects: list[bytes]) -> bytes:
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


def _wrap_line(line: str, width: int = 95) -> list[str]:
    if len(line) <= width:
        return [line]
    wrapped = []
    remaining = line
    while len(remaining) > width:
        split_at = remaining.rfind(" ", 0, width + 1)
        if split_at <= 0:
            split_at = width
        wrapped.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    wrapped.append(remaining)
    return wrapped


def _escape_pdf_text(value: str) -> str:
    safe_value = _pdf_safe_text(value)
    return safe_value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_safe_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(character for character in normalized if not unicodedata.combining(character))
    encoded = without_marks.encode(TEXT_ENCODING, errors="replace").decode(TEXT_ENCODING)
    return "".join(character if ord(character) >= 32 else " " for character in encoded)


def _optional(value: str | None) -> str:
    return value or "Non renseigne"


def _format_money(value: Decimal) -> str:
    return f"{value:.2f} EUR"


def _format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"
