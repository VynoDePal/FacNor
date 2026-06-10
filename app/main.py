from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from sqlalchemy import text

app = FastAPI(title="FacNor API")

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Simple query to verify database connection
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

from app.models import Invoice, Client, User
from app.services.numbering import get_next_sequence_value
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class InvoiceCreate(BaseModel):
    client_id: int
    user_id: int
    date: datetime
    due_date: Optional[datetime] = None
    lines: List[dict]

@app.post("/invoices/")
def create_invoice(invoice_data: InvoiceCreate, db: Session = Depends(get_db)):
    # Generate the sequential invoice number
    invoice_number = get_next_sequence_value(db, "invoice_seq", "F-")
    
    # Create the invoice
    new_invoice = Invoice(
        invoice_number=invoice_number,
        date=invoice_data.date,
        due_date=invoice_data.due_date,
        client_id=invoice_data.client_id,
        user_id=invoice_data.user_id,
        total_ht=0,
        total_tva=0,
        total_ttc=0,
        status='draft'
    )
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    
    return {"id": new_invoice.id, "invoice_number": new_invoice.invoice_number}

