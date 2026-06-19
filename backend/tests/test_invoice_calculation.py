from decimal import Decimal

from backend.app.invoice_calculation import calculate_invoice, calculate_invoice_item


def test_calculate_invoice_item_uses_decimal_math_for_line_totals() -> None:
    item = calculate_invoice_item(Decimal("3.00"), Decimal("19.99"), Decimal("5.50"))

    assert item.total_excluding_tax == Decimal("59.97")
    assert item.total_tax == Decimal("3.30")
    assert item.total_including_tax == Decimal("63.27")


def test_calculate_invoice_totals_are_sum_of_calculated_lines() -> None:
    invoice = calculate_invoice(
        [
            (Decimal("2.00"), Decimal("100.00"), Decimal("20.00")),
            (Decimal("3.00"), Decimal("19.99"), Decimal("5.50")),
            (Decimal("1.00"), Decimal("49.90"), Decimal("0.00")),
        ]
    )

    assert [item.total_including_tax for item in invoice.items] == [
        Decimal("240.00"),
        Decimal("63.27"),
        Decimal("49.90"),
    ]
    assert invoice.totals.total_excluding_tax == Decimal("309.87")
    assert invoice.totals.total_tax == Decimal("43.30")
    assert invoice.totals.total_including_tax == Decimal("353.17")
