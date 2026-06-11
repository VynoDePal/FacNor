from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.models.invoice import Invoice
from app.services.calculator import InvoiceCalculator
import io

class PDFService:
    @staticmethod
    def generate_invoice_pdf(invoice: Invoice):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Header
        elements.append(Paragraph("FACTURE", styles['Title']))
        elements.append(Spacer(1, 12))

        # Invoice Info
        invoice_info = [
            [f"Facture N°: {invoice.invoice_number}", f"Date: {invoice.date}"],
            [f"Échéance: {invoice.due_date if invoice.due_date else 'N/A'}", ""],
        ]
        t_info = Table(invoice_info)
        t_info.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT')]))
        elements.append(t_info)
        elements.append(Spacer(1, 24))

        # Client Info
        client = invoice.client
        client_info = [
            [f"Client: {client.name}"],
            [f"Adresse: {client.address if client.address else 'N/A'}"],
            [f"Email: {client.email if client.email else 'N/A'}"],
            [f"TVA: {client.vat_number if client.vat_number else 'N/A'}"],
        ]
        t_client = Table(client_info)
        t_client.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT')]))
        elements.append(t_client)
        elements.append(Spacer(1, 24))

        # Items Table
        data = [["Description", "Quantité", "Prix Unit. HT", "TVA %", "Total HT"]]
        for item in invoice.items:
            total_ht = item.quantity * item.unit_price_ht
            data.append([
                item.description,
                f"{item.quantity}",
                f"{item.unit_price_ht:.2f}",
                f"{item.vat_rate}%",
                f"{total_ht:.2f}"
            ])

        totals = InvoiceCalculator.calculate_totals(invoice.items)
        data.append(["", "", "", "Total HT:", f"{totals['total_ht']:.2f}"])
        data.append(["", "", "", "TVA:", f"{totals['total_vat']:.2f}"])
        data.append(["", "", "", "TOTAL TTC:", f"{totals['total_ttc']:.2f}"])

        t_items = Table(data)
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, -3), (-1, -1), 'RIGHT'),
        ]))
        elements.append(t_items)
        elements.append(Spacer(1, 24))

        # Legal Mentions
        legal_mentions = [
            Paragraph("Mentions Légales:", styles['Heading3']),
            Paragraph("Pénalités de retard : Taux légal en vigueur.", styles['Normal']),
            Paragraph("Indemnité forfaitaire pour frais de recouvrement : 40 €.", styles['Normal']),
            Paragraph(f"TVA acquittée sur les encaissements.", styles['Normal']),
        ]
        elements.extend(legal_mentions)

        doc.build(elements)
        pdf_value = buffer.getvalue()
        buffer.close()
        return pdf_value
