from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="user")

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    address = Column(String)
    vat_number = Column(String)  # Required for B2B
    is_business = Column(Boolean, default=False)  # True for B2B, False for B2C
    created_at = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="client")

class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, unique=True, nullable=False)
    date = Column(DateTime, nullable=False)
    due_date = Column(DateTime)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    total_ht = Column(Numeric(10, 2), nullable=False)
    total_tva = Column(Numeric(10, 2), nullable=False)
    total_ttc = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default='draft')  # e.g., draft, sent, paid, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="invoices")
    client = relationship("Client", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceLine(Base):
    __tablename__ = 'invoice_lines'
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    tax_rate = Column(Float, nullable=False)  # e.g., 20.0 for 20%
    total_ht = Column(Numeric(10, 2), nullable=False)
    total_tva = Column(Numeric(10, 2), nullable=False)
    total_ttc = Column(Numeric(10, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
