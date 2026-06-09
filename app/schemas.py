from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ClientBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    vat_number: Optional[str] = None
    siren: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    vat_number: Optional[str] = None
    siren: Optional[str] = None

class ClientOut(ClientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceLineBase(BaseModel):
    description: str
    quantity: float
    unit_price_ht: float
    tva_rate: float
    total_ht: float

class InvoiceLineCreate(InvoiceLineBase):
    pass

class InvoiceLineOut(InvoiceLineBase):
    id: int
    invoice_id: int

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    invoice_number: str
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    client_id: int
    total_ht: float = 0.0
    total_tva: float = 0.0
    total_ttc: float = 0.0
    status: str = "draft"

class InvoiceCreate(InvoiceBase):
    lines: list[InvoiceLineCreate] = []

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    total_ht: Optional[float] = None
    total_tva: Optional[float] = None
    total_ttc: Optional[float] = None
    status: Optional[str] = None

class InvoiceOut(InvoiceBase):
    id: int
    lines: list[InvoiceLineOut] = []

    class Config:
        from_attributes = True

