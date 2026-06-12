from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from app.models.models import Invoice, User, Client

def generate_invoice_pdf(invoice: Invoice, user: User) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12
    )
    normal_style = styles['Normal']
    
    elements = []
    
    # Header
    elements.append(Paragraph("FACTURE", title_style))
    elements.append(Spacer(1, 12))
    
    # Issuer and Client info
    issuer_info = [
        [Paragraph(f"<b>Émetteur :</b><br/>{user.username}<br/>{user.email}", normal_style),
         Paragraph(f"<b>Client :</b><br/>{invoice.client.name}<br/>{invoice.client.address or ''}<br/>{invoice.client.email or ''}<br/>SIREN: {invoice.client.siren or 'N/A'}<br/>TVA: {invoice.client.tva_number or 'N/A'}", normal_style)]
    ]
    t = Table(issuer_info, colWidths=[250, 250])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 24))
    
    # Invoice Details
    invoice_details = [
        [f"Facture N°: {invoice.invoice_number}", f"Date: {invoice.date_issued}"],
    ]
    t_details = Table(invoice_details, colWidths=[250, 250])
    t_details.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(t_details)
    elements.append(Spacer(1, 24))
    
    # Invoice Lines
    data = [["Description", "Quantité", "Prix Unit. HT", "TVA", "Total TTC"]]
    for line in invoice.lines:
        line_total_ttc = line.quantity * line.unit_price_ht * (1 + line.vat_rate / 100)
        data.append([
            line.description,
            f"{line.quantity}",
            f"{line.unit_price_ht:.2f} €",
            f"{line.vat_rate}%",
            f"{line_total_ttc:.2f} €"
        ])
    
    t_lines = Table(data, colWidths=[200, 50, 80, 50, 80])
    t_lines.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(t_lines)
    elements.append(Spacer(1, 24))
    
    # Totals
    totals_data = [
        ["Total HT", f"{invoice.total_ht:.2f} €"],
        ["Total TVA", f"{invoice.total_vat:.2f} €"],
        ["Total TTC", f"{invoice.total_ttc:.2f} €"],
    ]
    t_totals = Table(totals_data, colWidths=[200, 100], hAlign='RIGHT')
    t_totals.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (1, -1), 1, colors.black),
    ]))
    elements.append(t_totals)
    elements.append(Spacer(1, 48))
    
    # Legal Mentions
    legal_text = (
        "<b>Mentions Légales :</b><br/>"
        "Pénalités de retard : Taux d'intérêt légal en vigueur.<br/>"
        "Indemnité forfaitaire pour frais de recouvrement : 40 € (pour les professionnels).<br/>"
        "TVA acquittée sur les encaissements."
    )
    elements.append(Paragraph(legal_text, normal_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
