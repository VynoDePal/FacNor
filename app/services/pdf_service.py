from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from app.models.facture import Facture

class PDFService:
    def generate_invoice_pdf(self, facture: Facture, emitter_info: dict = None):
        if emitter_info is None:
            emitter_info = {
                "name": "Ma Société",
                "address": "123 Rue de l'Exemple, 75000 Paris",
                "email": "contact@masociete.fr",
                "siret": "123 456 789 00012"
            }

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Emitter Section
        emitter_text = f"<b>{emitter_info['name']}</b><br/>{emitter_info['address']}<br/>Email: {emitter_info['email']}<br/>SIRET: {emitter_info['siret']}"
        elements.append(Paragraph(emitter_text, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Invoice Info Section
        invoice_info = f"<b>Facture N°: {facture.numero}</b><br/>Date: {facture.date_facture}"
        elements.append(Paragraph(invoice_info, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Client Section
        client_info = f"<b>Client:</b><br/>{facture.client.nom}<br/>{facture.client.adresse or ''}<br/>Email: {facture.client.email or ''}<br/>TVA: {facture.client.tva_intracommunautaire or ''}"
        elements.append(Paragraph(client_info, styles['Normal']))
        elements.append(Spacer(1, 30))

        # Table Header
        data = [["Description", "Qté", "Prix Unit. HT", "TVA %", "Total TTC"]]
        
        # Table Rows
        for ligne in facture.lignes:
            data.append([
                ligne.description,
                f"{ligne.quantite:.2f}",
                f"{ligne.prix_unitaire_ht:.2f} €",
                f"{ligne.taux_tva:.2f}%",
                f"{ligne.montant_ttc:.2f} €"
            ])

        # Totals
        data.append(["", "", "", "Total HT", f"{facture.total_ht:.2f} €"])
        data.append(["", "", "", "Total TVA", f"{facture.total_tva:.2f} €"])
        data.append(["", "", "", "Total TTC", f"{facture.total_ttc:.2f} €"])

        table = Table(data, colWidths=[250, 50, 80, 60, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -3), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer
