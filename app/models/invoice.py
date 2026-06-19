import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    issued = "issued"
    paid = "paid"
    cancelled = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("user_id", "number", name="uq_invoices_user_number"),
        CheckConstraint("total_ht >= 0", name="ck_invoices_total_ht_non_negative"),
        CheckConstraint("total_tva >= 0", name="ck_invoices_total_tva_non_negative"),
        CheckConstraint("total_ttc >= 0", name="ck_invoices_total_ttc_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False, validate_strings=True, values_callable=lambda enum: [item.value for item in enum]), default=InvoiceStatus.draft, nullable=False
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    total_ht: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_tva: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_ttc: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    payment_terms: Mapped[str | None] = mapped_column(String(255))
    legal_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="invoices")
    client = relationship("Client", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.position")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_invoice_items_quantity_positive"),
        CheckConstraint("unit_price_ht >= 0", name="ck_invoice_items_unit_price_non_negative"),
        CheckConstraint("vat_rate >= 0", name="ck_invoice_items_vat_rate_non_negative"),
        CheckConstraint("line_total_ht >= 0", name="ck_invoice_items_total_ht_non_negative"),
        CheckConstraint("line_total_tva >= 0", name="ck_invoice_items_total_tva_non_negative"),
        CheckConstraint("line_total_ttc >= 0", name="ck_invoice_items_total_ttc_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(nullable=False, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price_ht: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    line_total_ht: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total_tva: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total_ttc: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
