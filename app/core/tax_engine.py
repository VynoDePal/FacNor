from typing import List
from app.models.models import InvoiceLine

def calculate_line_total(line: InvoiceLine) -> float:
    """
    Calculate the total TTC for a single invoice line.
    TTC = quantity * unit_price_ht * (1 + vat_rate)
    """
    # Assuming vat_rate is passed as a decimal (e.g., 0.20 for 20%)
    return line.quantity * line.unit_price_ht * (1 + line.vat_rate)

def calculate_invoice_totals(lines: List[InvoiceLine]):
    """
    Calculate totals for an invoice.
    Returns a dictionary with total_ht, total_vat, and total_ttc.
    """
    total_ht = 0.0
    total_vat = 0.0
    total_ttc = 0.0

    for line in lines:
        line_ht = line.quantity * line.unit_price_ht
        line_vat = line_ht * line.vat_rate
        line_ttc = line_ht + line_vat
        
        total_ht += line_ht
        total_vat += line_vat
        total_ttc += line_ttc

    return {
        "total_ht": round(total_ht, 2),
        "total_vat": round(total_vat, 2),
        "total_ttc": round(total_ttc, 2),
    }
