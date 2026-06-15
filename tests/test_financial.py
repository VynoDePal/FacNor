from decimal import Decimal

from app.financial import FinancialLineInput, calculate_invoice_totals, money


def test_money_rounds_half_up_to_two_decimals():
    assert money(Decimal("1.005")) == Decimal("1.01")
    assert money(Decimal("1.004")) == Decimal("1.00")


def test_invoice_totals_keep_ht_plus_tva_equal_ttc_for_multiple_lines():
    totals = calculate_invoice_totals(
        [
            FinancialLineInput("Prestation", Decimal("2"), Decimal("99.995"), Decimal("20")),
            FinancialLineInput("Produit", Decimal("3.5"), Decimal("12.345"), Decimal("5.5")),
            FinancialLineInput("Sans TVA", Decimal("1"), Decimal("10"), Decimal("0")),
        ]
    )

    assert totals.lines[0].excluding_tax == Decimal("199.99")
    assert totals.lines[0].tax == Decimal("40.00")
    assert totals.lines[0].including_tax == Decimal("239.99")
    assert totals.lines[1].excluding_tax == Decimal("43.21")
    assert totals.lines[1].tax == Decimal("2.38")
    assert totals.lines[1].including_tax == Decimal("45.59")
    assert totals.excluding_tax == Decimal("253.20")
    assert totals.tax == Decimal("42.38")
    assert totals.including_tax == Decimal("295.58")
    assert totals.excluding_tax + totals.tax == totals.including_tax


def test_empty_invoice_totals_are_zero():
    totals = calculate_invoice_totals([])

    assert totals.lines == []
    assert totals.excluding_tax == Decimal("0.00")
    assert totals.tax == Decimal("0.00")
    assert totals.including_tax == Decimal("0.00")
