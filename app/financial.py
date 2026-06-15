from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANTUM = Decimal("0.01")
VAT_DIVISOR = Decimal("100")


@dataclass(frozen=True)
class FinancialLineInput:
    description: str
    quantity: Decimal
    unit_price_excluding_tax: Decimal
    vat_rate: Decimal


@dataclass(frozen=True)
class FinancialLineTotals:
    line: FinancialLineInput
    excluding_tax: Decimal
    tax: Decimal
    including_tax: Decimal


@dataclass(frozen=True)
class FinancialTotals:
    lines: list[FinancialLineTotals]
    excluding_tax: Decimal
    tax: Decimal
    including_tax: Decimal


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_line_totals(line: FinancialLineInput) -> FinancialLineTotals:
    excluding_tax = money(line.quantity * line.unit_price_excluding_tax)
    tax = money(excluding_tax * line.vat_rate / VAT_DIVISOR)
    including_tax = money(excluding_tax + tax)
    return FinancialLineTotals(
        line=line,
        excluding_tax=excluding_tax,
        tax=tax,
        including_tax=including_tax,
    )


def calculate_invoice_totals(lines: list[FinancialLineInput]) -> FinancialTotals:
    line_totals = [calculate_line_totals(line) for line in lines]
    excluding_tax = money(sum((line.excluding_tax for line in line_totals), Decimal("0.00")))
    tax = money(sum((line.tax for line in line_totals), Decimal("0.00")))
    including_tax = money(excluding_tax + tax)
    return FinancialTotals(
        lines=line_totals,
        excluding_tax=excluding_tax,
        tax=tax,
        including_tax=including_tax,
    )
