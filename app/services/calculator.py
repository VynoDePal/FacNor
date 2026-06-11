from decimal import Decimal, ROUND_HALF_UP
from typing import List
from app.models.invoice_item import InvoiceItem

class InvoiceCalculator:
    @staticmethod
    def calculate_totals(items: List[InvoiceItem]):
        """
        Calculates totals for an invoice.
        Returns a dictionary with:
        - total_ht: Total amount before tax
        - total_vat: Total VAT amount
        - total_ttc: Total amount including tax
        All values are rounded to 2 decimal places using ROUND_HALF_UP.
        """
        total_ht = Decimal("0.00")
        total_vat = Decimal("0.00")

        for item in items:
            # Convert to Decimal for precision
            qty = Decimal(str(item.quantity))
            price = Decimal(str(item.unit_price_ht))
            vat_rate = Decimal(str(item.vat_rate))

            line_ht = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            line_vat = (line_ht * (vat_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            total_ht += line_ht
            total_vat += line_vat

        total_ttc = total_ht + total_vat

        return {
            "total_ht": float(total_ht),
            "total_vat": float(total_vat),
            "total_ttc": float(total_ttc)
        }
