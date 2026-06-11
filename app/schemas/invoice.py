from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class InvoiceItemCreate(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price_ht: float
    vat_rate: float

class InvoiceCreate(BaseModel):
    client_id: int
    date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[InvoiceItemCreate]
