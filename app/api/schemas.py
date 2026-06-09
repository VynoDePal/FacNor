from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: UUID
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ClientBase(BaseModel):
    client_type: str # 'B2B' or 'B2C'
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    vat_number: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    client_type: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    vat_number: Optional[str] = None

class ClientOut(ClientBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)

