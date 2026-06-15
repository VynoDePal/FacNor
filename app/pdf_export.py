from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from sqlite3 import Row

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.financial import money

DEFAULT_LEGAL_NOTICE = (
    "TVA exigible selon les règles fiscales en vigueur. "
    "Aucun escompte pour paiement anticipé. "
    "En cas de retard de paiement, des pénalités calculées au taux légal ainsi qu'une "
    "indemnité forfaitaire de 40 EUR pour frais de recouvrement sont dues."
)


def _money_text(value: Decimal, currency: str) -> str:
    return f"{money(value)} {currency}"


def _address_lines(row: Row) -> list[str]:
    lines = [row["name"]]
    if row["contact_full_name"]:
        lines.append(row["contact_full_name"])
    lines.append(row["address_line1"])
    if row["address_line2"]:
        lines.append(row["address_line2"])
    lines.append(f"{row['postal_code']} {row['city']}")
    lines.append(row["country"])
    if row["siren"]:
        lines.append(f"SIREN: {row['siren']}")
    if row["vat_number"]:
        lines.append(f"TVA intracommunautaire: {row['vat_number']}")
    if row["email"]:
        lines.append(f"Email: {row['email']}")
    if row["phone"]:
        lines.append(f"Téléphone: {row['phone']}")
    return lines


def _paragraph_lines(lines: list[str], style) -> list[Paragraph]:
    return [Paragraph(line, style) for line in lines]


def build_invoice_pdf(invoice, issuer: Row, client: Row) -> bytes:
    """Build a French compliant invoice PDF from existing invoice, user and client rows."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Facture {invoice.invoice_number}",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Facture {invoice.invoice_number}", styles["Title"]))
    story.append(Spacer(1, 0.4 * cm))

    issuer_lines = [issuer["company_name"], f"Contact: {issuer['full_name']}", f"Email: {issuer['email']}"]
    if issuer["company_siren"]:
        issuer_lines.append(f"SIREN: {issuer['company_siren']}")
    if issuer["company_vat_number"]:
        issuer_lines.append(f"TVA intracommunautaire: {issuer['company_vat_number']}")

    parties = Table(
        [
            [Paragraph("Émetteur", styles["Heading3"]), Paragraph("Client", styles["Heading3"])],
            [_paragraph_lines(issuer_lines, styles["BodyText"]), _paragraph_lines(_address_lines(client), styles["BodyText"])],
        ],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    parties.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(parties)
    story.append(Spacer(1, 0.5 * cm))

    metadata = [
        ["Numéro", invoice.invoice_number],
        ["Date d'émission", invoice.issue_date.isoformat()],
        ["Date d'échéance", invoice.due_date.isoformat() if invoice.due_date else "Non renseignée"],
        ["Statut", invoice.status],
        ["Devise", invoice.currency],
    ]
    metadata_table = Table(metadata, colWidths=[5 * cm, 12 * cm])
    metadata_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.append(metadata_table)
    story.append(Spacer(1, 0.5 * cm))

    line_rows = [["Description", "Qté", "PU HT", "TVA", "Total HT", "Total TVA", "Total TTC"]]
    for line in invoice.lines:
        line_rows.append(
            [
                Paragraph(line.description, styles["BodyText"]),
                str(line.quantity),
                _money_text(line.unit_price_excluding_tax, invoice.currency),
                f"{line.vat_rate} %",
                _money_text(line.line_total_excluding_tax, invoice.currency),
                _money_text(line.line_total_tax, invoice.currency),
                _money_text(line.line_total_including_tax, invoice.currency),
            ]
        )
    lines_table = Table(line_rows, repeatRows=1, colWidths=[5.2 * cm, 1.4 * cm, 2.1 * cm, 1.5 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm])
    lines_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(lines_table)
    story.append(Spacer(1, 0.5 * cm))

    totals = Table(
        [
            ["Total HT", _money_text(invoice.total_excluding_tax, invoice.currency)],
            ["Total TVA", _money_text(invoice.total_tax, invoice.currency)],
            ["Total TTC", _money_text(invoice.total_including_tax, invoice.currency)],
        ],
        colWidths=[5 * cm, 4 * cm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(totals)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Mentions légales", styles["Heading3"]))
    story.append(Paragraph(invoice.legal_notice or DEFAULT_LEGAL_NOTICE, styles["BodyText"]))

    document.build(story)
    return buffer.getvalue()
