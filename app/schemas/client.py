from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from datetime import datetime

class ClientBase(BaseModel):
    nom: str = Field(..., min_length=1)
    email: Optional[EmailStr] = None
    adresse: Optional[str] = None
    siat_siren: Optional[str] = None
    tva_intracommunautaire: Optional[str] = None
    type_client: str = Field(..., pattern="^(particulier|entreprise)$")

    @model_validator(mode='after')
    def check_entreprise_fields(self) -> 'ClientBase':
        if self.type_client == 'entreprise':
            if not self.siat_siren:
                raise ValueError('SIREN is required for entreprise clients')
            if not self.tva_intracommunautaire:
                raise ValueError('TVA intracommunautaire is required for entreprise clients')
        return self

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1)
    email: Optional[EmailStr] = None
    adresse: Optional[str] = None
    siat_siren: Optional[str] = None
    tva_intracommunautaire: Optional[str] = None
    type_client: Optional[str] = Field(None, pattern="^(particulier|entreprise)$")

class Client(ClientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
