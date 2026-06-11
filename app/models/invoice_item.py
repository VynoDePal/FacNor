from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit_price_ht = Column(Float, nullable=False)
    vat_rate = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="items")
