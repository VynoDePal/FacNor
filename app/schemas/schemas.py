from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional
from datetime import date

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ClientBase(BaseModel):
    name: str
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    siren: Optional[str] = None
    tva_number: Optional[str] = None
    is_company: bool = False

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class InvoiceLineBase(BaseModel):
    description: str
    quantity: float
    unit_price_ht: float
    vat_rate: float

class InvoiceLineCreate(InvoiceLineBase):
    pass

class InvoiceLineResponse(InvoiceLineBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class InvoiceBase(BaseModel):
    invoice_number: str
    client_id: int
    date_issued: date
    date_due: Optional[date] = None
    status: str = "draft"
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    lines: List[InvoiceLineCreate]

class InvoiceResponse(InvoiceBase):
    id: int
    user_id: int
    lines: List[InvoiceLineResponse]
    total_ht: float
    total_vat: float
    total_ttc: float
    model_config = ConfigDict(from_attributes=True)
