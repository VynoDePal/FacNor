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

