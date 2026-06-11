from pydantic import BaseModel
from typing import List
from datetime import date

class InvoiceItemRead(BaseModel):
    id: int
    description: str
    quantity: float
    unit_price_ht: float
    vat_rate: float

    class Config:
        from_attributes = True

class InvoiceRead(BaseModel):
    id: int
    user_id: int
    client_id: int
    invoice_number: str
    date: date
    due_date: date | None
    status: str
    notes: str | None
    total_ht: float
    total_vat: float
    total_ttc: float
    items: List[InvoiceItemRead]

    class Config:
        from_attributes = True
