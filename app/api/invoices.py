from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Invoice, InvoiceLine
from app.schemas.schemas import InvoiceCreate, InvoiceResponse
from app.api.deps import get_current_user
from app.models.models import User
from app.core.sequencing import get_next_invoice_number

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("/", response_model=list[InvoiceResponse])
def read_invoices(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return db.query(Invoice).filter(Invoice.user_id == current_user.id).all()

@router.post("/", response_model=InvoiceResponse)
def create_invoice(
    invoice: InvoiceCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Use provided invoice number or generate a new one
    invoice_number = invoice.invoice_number or get_next_invoice_number(db)
    
    db_invoice = Invoice(
        invoice_number=invoice_number,
        client_id=invoice.client_id,
        user_id=current_user.id, # Force the user_id to be the current authenticated user
        date_issued=invoice.date_issued,
        date_due=invoice.date_due,
        status=invoice.status,
        notes=invoice.notes
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    for line in invoice.lines:
        db_line = InvoiceLine(**line.model_dump(), invoice_id=db_invoice.id)
        db.add(db_line)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice
