from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class ClientBase(BaseModel):
    name: str
    email: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    siren: Optional[str] = None
    vat_number: Optional[str] = None
    is_company: bool = False

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    siren: Optional[str] = None
    vat_number: Optional[str] = None
    is_company: Optional[bool] = None

class ClientRead(ClientBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
