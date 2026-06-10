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
