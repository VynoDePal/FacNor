from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models import models
from app.schemas import InvoiceCreate, InvoiceOut, InvoiceUpdate
from app.services.numbering import get_next_invoice_number

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"]
)

@router.post("/", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    # Check if client exists
    client = db.query(models.Client).filter(models.Client.id == invoice.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Generate invoice number if not provided
    invoice_num = invoice.invoice_number or get_next_invoice_number(db)

    # Create invoice object
    db_invoice = models.Invoice(
        invoice_number=invoice_num,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        client_id=invoice.client_id,
        total_ht=invoice.total_ht,
        total_tva=invoice.total_tva,
        total_ttc=invoice.total_ttc,
        status=invoice.status
    )
    db.add(db_invoice)
    db.flush() # Get the invoice ID

    # Create invoice lines
    for line_data in invoice.lines:
        db_line = models.InvoiceLine(
            invoice_id=db_invoice.id,
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price_ht=line_data.unit_price_ht,
            tva_rate=line_data.tva_rate,
            total_ht=line_data.total_ht
        )
        db.add(db_line)

    # Recalculate totals based on lines (optional but recommended)
    total_ht = sum(line.total_ht for line in invoice.lines)
    total_tva = sum(line.quantity * line.unit_price_ht * (line.tva_rate / 100) for line in invoice.lines)
    total_ttc = total_ht + total_tva
    
    db_invoice.total_ht = total_ht
    db_invoice.total_tva = total_tva
    db_invoice.total_ttc = total_ttc

    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.get("/", response_model=List[InvoiceOut])
def read_invoices(client_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Invoice)
    if client_id:
        query = query.filter(models.Invoice.client_id == client_id)
    return query.all()

@router.get("/{invoice_id}", response_model=InvoiceOut)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)):
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@router.put("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: int, invoice_update: InvoiceUpdate, db: Session = Depends(get_db)):
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    update_data = invoice_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_invoice, key, value)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    db.delete(db_invoice)
    db.commit()
    return None
