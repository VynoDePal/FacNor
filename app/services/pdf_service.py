from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from app.core.config import settings
from app.models.models import Invoice

import io

def generate_invoice_pdf(invoice: Invoice):
    """
    Generates a PDF for a given invoice and returns it as a byte stream.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_RIGHT
    )
    
    normal_style = styles['Normal']
    
    elements = []

    # --- Header ---
    # Company Info (Left) | Invoice Title (Right)
    header_data = [
        [
            Paragraph(f"<b>{settings.COMPANY_NAME}</b><br/>{settings.COMPANY_ADDRESS}<br/>SIREN: {settings.COMPANY_SIREN}<br/>TVA: {settings.COMPANY_VAT}<br/>{settings.COMPANY_EMAIL}<br/>{settings.COMPANY_PHONE}", normal_style),
            Paragraph("FACTURE", title_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[300, 200])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20))

    # --- Client Info ---
    client_info = f"<b>Client :</b><br/>{invoice.client.name}<br/>{invoice.client.address or ''}<br/>TVA: {invoice.client.vat_number or 'N/A'}<br/>SIREN: {invoice.client.siren or 'N/A'}"
    elements.append(Paragraph(client_info, normal_style))
    elements.append(Spacer(1, 20))

    # --- Invoice Details ---
    invoice_details = [
        [Paragraph(f"<b>Numéro de facture :</b> {invoice.invoice_number}", normal_style), 
         Paragraph(f"<b>Date d'émission :</b> {invoice.issue_date.strftime('%d/%m/%Y') if invoice.issue_date else 'N/A'}", normal_style)],
        [Paragraph(f"<b>Date d'échéance :</b> {invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else 'N/A'}", normal_style), ""]
    ]
    details_table = Table(invoice_details, colWidths=[250, 250])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 20))

    # --- Line Items ---
    # Table Header
    data = [["Description", "Quantité", "Prix Unitaire HT", "TVA %", "Total HT"]]
    
    # Table Body
    for line in invoice.lines:
        data.append([
            line.description,
            str(line.quantity),
            f"{float(line.unit_price_ht):.2f}",
            f"{float(line.tva_rate):.2f}%",
            f"{float(line.total_ht):.2f}"
        ])
    
    # Table Footer (Totals)
    data.append(["", "", "", "Total HT", f"{float(invoice.total_ht):.2f}"])
    data.append(["", "", "", "Total TVA", f"{float(invoice.total_tva):.2f}"])
    data.append(["", "", "", "Total TTC", f"{float(invoice.total_ttc):.2f}"])

    line_table = Table(data, colWidths=[200, 70, 100, 70, 100])
    line_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -3), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 30))

    # --- Legal Mentions ---
    legal_mentions = [
        "TVA acquittée sur les encaissements.",
        "En cas de retard de paiement, une indemnité forfaitaire pour frais de recouvrement de 40€ est due.",
        "Pénalités de retard au taux annuel de 10% à compter de la date d'échéance."
    ]
    for mention in legal_mentions:
        elements.append(Paragraph(mention, normal_style))
        elements.append(Spacer(1, 6))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
