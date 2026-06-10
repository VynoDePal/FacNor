from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
from typing import Optional
import decimal



def get_client(db: Session, client_id: int):
    return db.query(models.Client).filter(models.Client.id == client_id).first()

def get_clients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Client).offset(skip).limit(limit).all()

def create_client(db: Session, client: schemas.ClientCreate):
    db_client = models.Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def update_client(db: Session, client_id: int, client: schemas.ClientUpdate):
    db_client = get_client(db, client_id)
    if not db_client:
        return None
    
    update_data = client.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_client, key, value)
    
    db.commit()
    db.refresh(db_client)
    return db_client

def delete_client(db: Session, client_id: int):
    db_client = get_client(db, client_id)
    if db_client:
        db.delete(db_client)
        db.commit()
        return True
    return False

def get_invoices(db: Session, user_id: int, skip: int = 0, limit: int = 100, client_id: Optional[int] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    query = db.query(models.Invoice).filter(models.Invoice.user_id == user_id)
    if client_id:
        query = query.filter(models.Invoice.client_id == client_id)
    if start_date:
        query = query.filter(models.Invoice.date >= start_date)
    if end_date:
        query = query.filter(models.Invoice.date <= end_date)
    return query.offset(skip).limit(limit).all()

def get_invoice(db: Session, invoice_id: int, user_id: int):
    return db.query(models.Invoice).filter(models.Invoice.id == invoice_id, models.Invoice.user_id == user_id).first()

def create_invoice(db: Session, invoice: schemas.InvoiceCreate, user_id: int):
    # Generate a unique invoice number if not provided (in a real app, this would be more complex)
    import uuid
    invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    db_invoice = models.Invoice(
        **invoice.model_dump(exclude={'lines', 'user_id'}),
        invoice_number=invoice_number,
        user_id=user_id
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    for line in invoice.lines:
        db_line = models.InvoiceLine(**line.model_dump(), invoice_id=db_invoice.id)
        db.add(db_line)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def update_invoice(db: Session, invoice_id: int, invoice_update: schemas.InvoiceUpdate, user_id: int):
    db_invoice = get_invoice(db, invoice_id, user_id)
    if not db_invoice:
        return None
    
    update_data = invoice_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_invoice, key, value)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def delete_invoice(db: Session, invoice_id: int, user_id: int):
    db_invoice = get_invoice(db, invoice_id, user_id)
    if db_invoice:
        db.delete(db_invoice)
        db.commit()
        return True
    return False
