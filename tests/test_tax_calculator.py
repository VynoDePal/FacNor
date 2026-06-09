import pytest
from decimal import Decimal
from app.services.tax_calculator import TaxCalculator

def test_calculate_line_total():
    # Basic calculation
    assert TaxCalculator.calculate_line_total(2, 50.0, 20.0) == Decimal("100.00")
    # Precision test
    assert TaxCalculator.calculate_line_total(1, 10.333, 20.0) == Decimal("10.33")
    assert TaxCalculator.calculate_line_total(1, 10.336, 20.0) == Decimal("10.34")
    # Zero quantity
    assert TaxCalculator.calculate_line_total(0, 50.0, 20.0) == Decimal("0.00")

def test_calculate_line_tva():
    # Basic calculation: 100 * 20% = 20
    assert TaxCalculator.calculate_line_tva(Decimal("100.00"), 20.0) == Decimal("20.00")
    # Precision test: 10.33 * 20% = 2.066 -> 2.07
    assert TaxCalculator.calculate_line_tva(Decimal("10.33"), 20.0) == Decimal("2.07")
    # Precision test: 10.32 * 20% = 2.064 -> 2.06
    assert TaxCalculator.calculate_line_tva(Decimal("10.32"), 20.0) == Decimal("2.06")
    # Zero TVA rate
    assert TaxCalculator.calculate_line_tva(Decimal("100.00"), 0.0) == Decimal("0.00")

def test_calculate_invoice_totals():
    lines_data = [
        {"quantity": 2, "unit_price_ht": 50.0, "tva_rate": 20.0}, # HT: 100.00, TVA: 20.00
        {"quantity": 1, "unit_price_ht": 20.0, "tva_rate": 20.0}, # HT: 20.00, TVA: 4.00
    ]
    result = TaxCalculator.calculate_invoice_totals(lines_data)
    assert result.total_ht == Decimal("120.00")
    assert result.total_tva == Decimal("24.00")
    assert result.total_ttc == Decimal("144.00")

def test_calculate_invoice_totals_precision():
    lines_data = [
        {"quantity": 1, "unit_price_ht": 10.333, "tva_rate": 20.0}, # HT: 10.33, TVA: 2.07
        {"quantity": 1, "unit_price_ht": 10.336, "tva_rate": 20.0}, # HT: 10.34, TVA: 2.07
    ]
    result = TaxCalculator.calculate_invoice_totals(lines_data)
    # HT = 10.33 + 10.34 = 20.67
    # TVA = 2.07 + 2.07 = 4.14
    # TTC = 20.67 + 4.14 = 24.81
    assert result.total_ht == Decimal("20.67")
    assert result.total_tva == Decimal("4.14")
    assert result.total_ttc == Decimal("24.81")

def test_empty_invoice():
    result = TaxCalculator.calculate_invoice_totals([])
    assert result.total_ht == Decimal("0.00")
    assert result.total_tva == Decimal("0.00")
    assert result.total_ttc == Decimal("0.00")
