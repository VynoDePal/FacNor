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

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def read_invoice(
    invoice_id: int,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if db_invoice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this invoice")
    return db_invoice

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

@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if db_invoice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this invoice")
    
    # Update invoice details
    if invoice_update.invoice_number:
        db_invoice.invoice_number = invoice_update.invoice_number
    db_invoice.client_id = invoice_update.client_id
    db_invoice.date_issued = invoice_update.date_issued
    if invoice_update.date_due:
        db_invoice.date_due = invoice_update.date_due
    db_invoice.status = invoice_update.status
    db_invoice.notes = invoice_update.notes
    
    # Update lines: simplest way is to delete old lines and add new ones
    db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice_id).delete()
    for line in invoice_update.lines:
        db_line = InvoiceLine(**line.model_dump(), invoice_id=db_invoice.id)
        db.add(db_line)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if db_invoice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this invoice")
    
    db.delete(db_invoice)
    db.commit()
    return {"detail": "Invoice deleted successfully"}
