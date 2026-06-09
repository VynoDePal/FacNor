from decimal import Decimal, ROUND_HALF_UP
from typing import List, NamedTuple

class CalculationResult(NamedTuple):
    total_ht: Decimal
    total_tva: Decimal
    total_ttc: Decimal

class TaxCalculator:
    @staticmethod
    def calculate_line_total(quantity: float, unit_price_ht: float, tva_rate: float) -> Decimal:
        """
        Calculates the total HT for a single line.
        Result is rounded to 2 decimal places.
        """
        qty = Decimal(str(quantity))
        price = Decimal(str(unit_price_ht))
        return (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_line_tva(total_ht: Decimal, tva_rate: float) -> Decimal:
        """
        Calculates the TVA for a single line.
        Result is rounded to 2 decimal places.
        """
        rate = Decimal(str(tva_rate)) / Decimal("100")
        return (total_ht * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_invoice_totals(cls, lines_data: List[dict]) -> CalculationResult:
        """
        Calculates the totals for an entire invoice based on its lines.
        lines_data should be a list of dictionaries containing 'quantity', 'unit_price_ht', and 'tva_rate'.
        """
        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")

        for line in lines_data:
            qty = line.get('quantity', 0)
            price = line.get('unit_price_ht', 0)
            rate = line.get('tva_rate', 0)
            
            line_ht = cls.calculate_line_total(qty, price, rate)
            line_tva = cls.calculate_line_tva(line_ht, rate)
            
            total_ht += line_ht
            total_tva += line_tva

        total_ttc = total_ht + total_tva
        
        return CalculationResult(
            total_ht=total_ht,
            total_tva=total_tva,
            total_ttc=total_ttc
        )
