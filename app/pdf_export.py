from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass(frozen=True)
class ClientPdfData:
    name: str
    client_type: str
    email: str | None = None
    address: str | None = None
    siren: str | None = None
    vat_number: str | None = None


def _money(value: Decimal) -> str:
    return f"{Decimal(value):.2f} EUR"


def _line(value: str | None) -> str:
    return value if value else "-"


def generate_invoice_pdf(
    invoice: Any,
    client: ClientPdfData,
    issuer: Any,
) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        pageCompression=0,
        title=f"Facture {invoice.invoice_number}",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Facture {invoice.invoice_number}", styles["Title"]))
    story.append(Spacer(1, 8 * mm))

    issuer_lines = [
        "<b>Émetteur</b>",
        _line(issuer.full_name),
        issuer.email,
    ]
    client_lines = [
        "<b>Client</b>",
        client.name,
        _line(client.email),
        _line(client.address),
    ]
    if client.client_type == "company":
        client_lines.extend([
            f"SIREN : {_line(client.siren)}",
            f"TVA intracommunautaire : {_line(client.vat_number)}",
        ])

    parties = Table(
        [[Paragraph("<br/>".join(issuer_lines), styles["BodyText"]), Paragraph("<br/>".join(client_lines), styles["BodyText"])]],
        colWidths=[82 * mm, 82 * mm],
    )
    parties.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(parties)
    story.append(Spacer(1, 7 * mm))

    metadata = Table(
        [
            ["Date d'émission", invoice.issue_date, "Échéance", _line(invoice.due_date)],
            ["Statut", invoice.status, "Devise", "EUR"],
        ],
        colWidths=[40 * mm, 42 * mm, 40 * mm, 42 * mm],
    )
    metadata.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metadata)
    story.append(Spacer(1, 7 * mm))

    item_rows = [["Description", "Qté", "PU HT", "TVA", "Total HT", "Total TVA", "Total TTC"]]
    for item in invoice.items:
        item_rows.append([
            Paragraph(item.description, styles["BodyText"]),
            str(item.quantity),
            _money(item.unit_price_excluding_tax),
            f"{item.vat_rate} %",
            _money(item.line_total_excluding_tax),
            _money(item.line_total_vat),
            _money(item.line_total_including_tax),
        ])

    items_table = Table(item_rows, colWidths=[50 * mm, 15 * mm, 23 * mm, 18 * mm, 24 * mm, 24 * mm, 26 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 7 * mm))

    totals = Table(
        [
            ["Total HT", _money(invoice.total_excluding_tax)],
            ["Total TVA", _money(invoice.total_vat)],
            ["Total TTC", _money(invoice.total_including_tax)],
        ],
        colWidths=[45 * mm, 35 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#E8EEF7")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(totals)
    story.append(Spacer(1, 7 * mm))
    story.append(Paragraph("Facture générée par FacNor conformément aux données enregistrées.", styles["Italic"]))

    document.build(story)
    return buffer.getvalue()
