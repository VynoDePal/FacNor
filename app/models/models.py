from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime
from datetime import timezone

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    address = Column(String)
    vat_number = Column(String)  # Numéro de TVA intracommunautaire
    siren = Column(String)  # Numéro SIREN
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    invoices = relationship("Invoice", back_populates="client")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    issue_date = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    due_date = Column(DateTime)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    total_ht = Column(Float, default=0.0)
    total_tva = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)
    status = Column(String, default="draft") # draft, sent, paid, cancelled
    
    client = relationship("Client", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price_ht = Column(Float, nullable=False)
    tva_rate = Column(Float, nullable=False) # e.g., 20.0
    total_ht = Column(Float, nullable=False)
    
    invoice = relationship("Invoice", back_populates="lines")
