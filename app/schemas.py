from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class ClientBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    vat_number: Optional[str] = None
    is_business: bool = False

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    vat_number: Optional[str] = None
    is_business: Optional[bool] = None

class Client(ClientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class InvoiceLineBase(BaseModel):
    description: str
    quantity: float
    unit_price: float
    tax_rate: float
    total_ht: float
    total_tva: float
    total_ttc: float

class InvoiceLineCreate(InvoiceLineBase):
    pass

class InvoiceLine(InvoiceLineBase):
    id: int
    invoice_id: int

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    date: datetime
    due_date: Optional[datetime] = None
    client_id: int
    user_id: int
    total_ht: float
    total_tva: float
    total_ttc: float
    status: str = 'draft'

class InvoiceCreate(InvoiceBase):
    lines: list[InvoiceLineCreate]

class Invoice(InvoiceBase):
    id: int
    invoice_number: str
    created_at: datetime
    lines: list[InvoiceLine]

    class Config:
        from_attributes = True

