from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TaxLineInput:
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal


@dataclass(frozen=True)
class TaxLineTotals:
    total_excluding_tax: Decimal
    total_tax: Decimal
    total_including_tax: Decimal


@dataclass(frozen=True)
class InvoiceTaxTotals:
    lines: list[TaxLineTotals]
    total_excluding_tax: Decimal
    total_tax: Decimal
    total_including_tax: Decimal


def decimal_from_number(value: float | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def calculate_line_totals(line: TaxLineInput) -> TaxLineTotals:
    total_excluding_tax = line.quantity * line.unit_price
    multiplier = Decimal(1) + (line.tax_rate / Decimal(100))
    total_including_tax = line.quantity * line.unit_price * multiplier
    total_tax = total_including_tax - total_excluding_tax
    return TaxLineTotals(
        total_excluding_tax=total_excluding_tax,
        total_tax=total_tax,
        total_including_tax=total_including_tax,
    )


def calculate_invoice_totals(lines: list[TaxLineInput]) -> InvoiceTaxTotals:
    line_totals = [calculate_line_totals(line) for line in lines]
    return InvoiceTaxTotals(
        lines=line_totals,
        total_excluding_tax=sum(
            (line.total_excluding_tax for line in line_totals), Decimal(0)
        ),
        total_tax=sum((line.total_tax for line in line_totals), Decimal(0)),
        total_including_tax=sum(
            (line.total_including_tax for line in line_totals), Decimal(0)
        ),
    )
