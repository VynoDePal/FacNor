from sqlalchemy.orm import Session
import random
import string
from . import models, schemas
from datetime import datetime
import decimal

from typing import Optional


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

def get_invoice(db: Session, invoice_id: int):
    return db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

def get_invoices(db: Session, skip: int = 0, limit: int = 100, client_id: Optional[int] = None, date: Optional[datetime] = None):
    query = db.query(models.Invoice)
    if client_id:
        query = query.filter(models.Invoice.client_id == client_id)
    if date:
        query = query.filter(models.Invoice.date == date)
    return query.offset(skip).limit(limit).all()

def create_invoice(db: Session, invoice: schemas.InvoiceCreate):
    # Calculate totals for each line and for the invoice
    total_ht = 0
    total_tva = 0
    total_ttc = 0
    
    invoice_lines = []
    for line_data in invoice.lines:
        # Calculate line totals
        line_ht = line_data.quantity * line_data.unit_price
        line_tva = line_ht * (line_data.tax_rate / 100)
        line_ttc = line_ht + line_tva
        
        total_ht += line_ht
        total_tva += line_tva
        total_ttc += line_ttc
        
        invoice_lines.append(models.InvoiceLine(
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            tax_rate=line_data.tax_rate,
            total_ht=line_ht,
            total_tva=line_tva,
            total_ttc=line_ttc
        ))

    # Generate invoice number (simplified but more unique)
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{ ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"
    
    db_invoice = models.Invoice(
        date=invoice.date,
        due_date=invoice.due_date,
        client_id=invoice.client_id,
        user_id=invoice.user_id,
        total_ht=total_ht,
        total_tva=total_tva,
        total_ttc=total_ttc,
        status=invoice.status,
        invoice_number=invoice_number,
        lines=invoice_lines
    )
    
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def update_invoice(db: Session, invoice_id: int, invoice: schemas.InvoiceUpdate):
    db_invoice = get_invoice(db, invoice_id)
    if not db_invoice:
        return None
    
    update_data = invoice.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_invoice, key, value)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def delete_invoice(db: Session, invoice_id: int):
    db_invoice = get_invoice(db, invoice_id)
    if db_invoice:
        db.delete(db_invoice)
        db.commit()
        return True
    return False

