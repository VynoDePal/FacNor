from fastapi import FastAPI, Depends, HTTPException
from fastapi import status as fastapi_status
from sqlalchemy.orm import Session
from app.core.database import init_db, get_db
from app.models.user import User
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.schemas.invoice import InvoiceCreate
from app.schemas.invoice_read import InvoiceRead
from app.services.calculator import InvoiceCalculator
from app.services.numbering import InvoiceNumberingService

app = FastAPI(title="FacNor API")

@app.on_event("startup")
async def on_startup():
    init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to FacNor API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/invoices/", response_model=InvoiceRead, status_code=fastapi_status.HTTP_201_CREATED)
async def create_invoice(invoice_data: InvoiceCreate, user_id: int, db: Session = Depends(get_db)):
    # user_id is passed as query param for now, as auth is not yet implemented
    
    # 1. Generate sequential number
    invoice_number = InvoiceNumberingService.generate_next_number(db, user_id)
    
    # 2. Create invoice
    db_invoice = Invoice(
        user_id=user_id,
        client_id=invoice_data.client_id,
        invoice_number=invoice_number,
        date=invoice_data.date,
        due_date=invoice_data.due_date,
        notes=invoice_data.notes,
        status="draft"
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    # 3. Create invoice items
    invoice_items = []
    for item_data in invoice_data.items:
        item = InvoiceItem(
            invoice_id=db_invoice.id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price_ht=item_data.unit_price_ht,
            vat_rate=item_data.vat_rate
        )
        db.add(item)
        invoice_items.append(item)
    
    db.commit()
    db.refresh(db_invoice)
    
    # 4. Calculate totals
    totals = InvoiceCalculator.calculate_totals(db_invoice.items)
    
    # We don't store totals in the DB based on the current schema.sql
    # But we return them in the response.
    # To match InvoiceRead, we need to dynamically add totals.
    
    # Since InvoiceRead is a Pydantic model, we can't just add attributes to the SQLAlchemy model.
    # We can create a custom response object or modify InvoiceRead to allow dynamic values.
    # For the purpose of this task, we will return a dictionary or a modified Pydantic model.
    
    return {
        **InvoiceRead.from_orm(db_invoice).dict(),
        **totals
    }

@app.get("/invoices/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: int, user_id: int, db: Session = Depends(get_db)):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    totals = InvoiceCalculator.calculate_totals(db_invoice.items)
    
    # Combine SQLAlchemy model with calculated totals
    invoice_dict = InvoiceRead.from_orm(db_invoice).dict()
    invoice_dict.update(totals)
    return invoice_dict
