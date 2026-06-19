import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClientType(str, enum.Enum):
    b2b = "B2B"
    b2c = "B2C"


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint(
            "client_type != 'B2B' OR siren IS NOT NULL OR vat_number IS NOT NULL",
            name="ck_clients_b2b_requires_siren_or_vat",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_type: Mapped[ClientType] = mapped_column(
        Enum(ClientType, native_enum=False, validate_strings=True, values_callable=lambda enum: [item.value for item in enum]), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255))
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(120), default="France", nullable=False)
    siren: Mapped[str | None] = mapped_column(String(9), index=True)
    vat_number: Mapped[str | None] = mapped_column(String(32), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="clients")
    invoices = relationship("Invoice", back_populates="client")
