from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class CalculatedInvoiceItem:
    total_excluding_tax: Decimal
    total_tax: Decimal
    total_including_tax: Decimal


@dataclass(frozen=True)
class CalculatedInvoiceTotals:
    total_excluding_tax: Decimal
    total_tax: Decimal
    total_including_tax: Decimal


@dataclass(frozen=True)
class CalculatedInvoice:
    items: list[CalculatedInvoiceItem]
    totals: CalculatedInvoiceTotals


def calculate_invoice(items: list[tuple[Decimal, Decimal, Decimal]]) -> CalculatedInvoice:
    calculated_items = [calculate_invoice_item(*item) for item in items]
    totals = CalculatedInvoiceTotals(
        total_excluding_tax=_money(sum(item.total_excluding_tax for item in calculated_items)),
        total_tax=_money(sum(item.total_tax for item in calculated_items)),
        total_including_tax=_money(sum(item.total_including_tax for item in calculated_items)),
    )
    return CalculatedInvoice(items=calculated_items, totals=totals)


def calculate_invoice_item(quantity: Decimal, unit_price_excluding_tax: Decimal, vat_rate: Decimal) -> CalculatedInvoiceItem:
    total_excluding_tax = _money(quantity * unit_price_excluding_tax)
    total_tax = _money(total_excluding_tax * vat_rate / Decimal("100"))
    return CalculatedInvoiceItem(
        total_excluding_tax=total_excluding_tax,
        total_tax=total_tax,
        total_including_tax=_money(total_excluding_tax + total_tax),
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
