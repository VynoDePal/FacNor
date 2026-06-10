from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class LigneFactureBase(BaseModel):
    description: str = Field(..., min_length=1)
    quantite: float = Field(..., gt=0)
    prix_unitaire_ht: float = Field(..., ge=0)
    taux_tva: float = Field(..., ge=0)

class LigneFactureCreate(LigneFactureBase):
    pass

class LigneFacture(LigneFactureBase):
    id: int

    class Config:
        from_attributes = True

class FactureBase(BaseModel):
    numero: str = Field(..., min_length=1)
    client_id: int
    date_facture: date
    date_echeance: Optional[date] = None
    statut: str = Field("brouillon", pattern="^(brouillon|envoyee|payee|annulee)$")
    notes: Optional[str] = None

class FactureCreate(FactureBase):
    lignes: List[LigneFactureCreate] = []

class FactureUpdate(BaseModel):
    numero: Optional[str] = Field(None, min_length=1)
    client_id: Optional[int] = None
    date_facture: Optional[date] = None
    date_echeance: Optional[date] = None
    statut: Optional[str] = Field(None, pattern="^(brouillon|envoyee|payee|annulee)$")
    notes: Optional[str] = None

class Facture(FactureBase):
    id: int
    created_at: datetime
    lignes: List[LigneFacture] = []

    class Config:
        from_attributes = True
