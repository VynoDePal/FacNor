from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models import models
from app.schemas import InvoiceCreate, InvoiceOut, InvoiceUpdate
from app.services.numbering import get_next_invoice_number
from app.services.pdf_service import generate_invoice_pdf

from app.services.tax_calculator import TaxCalculator

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
    lines_data = []
    for line_data in invoice.lines:
        # Use TaxCalculator to ensure line total is correct
        line_total_ht = TaxCalculator.calculate_line_total(
            line_data.quantity, line_data.unit_price_ht, line_data.tva_rate
        )
        
        db_line = models.InvoiceLine(
            invoice_id=db_invoice.id,
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price_ht=line_data.unit_price_ht,
            tva_rate=line_data.tva_rate,
            total_ht=line_total_ht
        )
        db.add(db_line)
        lines_data.append({
            'quantity': line_data.quantity,
            'unit_price_ht': line_data.unit_price_ht,
            'tva_rate': line_data.tva_rate
        })

    # Recalculate totals based on lines
    totals = TaxCalculator.calculate_invoice_totals(lines_data)
    
    db_invoice.total_ht = totals.total_ht
    db_invoice.total_tva = totals.total_tva
    db_invoice.total_ttc = totals.total_ttc

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

@router.get("/{invoice_id}/pdf", response_class=StreamingResponse)
def download_invoice_pdf(invoice_id: int, db: Session = Depends(get_db)):
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Use joinedload or similar if needed, but here we just need the client and lines
    # Since they are relationships, they'll be lazy loaded.
    
    pdf_buffer = generate_invoice_pdf(db_invoice)
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=invoice_{db_invoice.invoice_number}.pdf"}
    )
