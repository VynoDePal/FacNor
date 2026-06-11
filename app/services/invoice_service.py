from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.services.calculator import InvoiceCalculator

class InvoiceService:
    @staticmethod
    def format_invoice_response(invoice: Invoice):
        """
        Converts an Invoice model to a dictionary including calculated totals.
        """
        totals = InvoiceCalculator.calculate_totals(invoice.items)
        return {
            "id": invoice.id,
            "user_id": invoice.user_id,
            "client_id": invoice.client_id,
            "invoice_number": invoice.invoice_number,
            "date": invoice.date,
            "due_date": invoice.due_date,
            "status": invoice.status,
            "notes": invoice.notes,
            "items": invoice.items,
            **totals
        }
