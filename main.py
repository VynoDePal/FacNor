from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, engine
from app.models.models import User, Client, Invoice, InvoiceLine
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database using schema.sql to ensure consistency between tests and production
    with open("schema.sql", "r") as f:
        schema = f.read()
    
    import sqlite3
    db_path = engine.url.database
    # If the database is in-memory, this might not work as expected for the app
    # but we are using a file by default: sqlite:///./facnor.db
    with sqlite3.connect(db_path) as sqlite_conn:
        sqlite_conn.executescript(schema)
    yield

app = FastAPI(title="FacNor API", lifespan=lifespan)

# Pydantic schemas for API
class ClientBase(BaseModel):
    name: str
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    siren: Optional[str] = None
    tva_number: Optional[str] = None
    is_company: bool = False

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class InvoiceLineBase(BaseModel):
    description: str
    quantity: float
    unit_price_ht: float
    vat_rate: float

class InvoiceLineCreate(InvoiceLineBase):
    pass

class InvoiceLineResponse(InvoiceLineBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class InvoiceBase(BaseModel):
    invoice_number: str
    client_id: int
    user_id: int
    date_issued: date
    date_due: Optional[date] = None
    status: str = "draft"
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    lines: List[InvoiceLineCreate]

class InvoiceResponse(InvoiceBase):
    id: int
    lines: List[InvoiceLineResponse]
    model_config = ConfigDict(from_attributes=True)

@app.get("/clients", response_model=List[ClientResponse])
def read_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()

@app.post("/clients", response_model=ClientResponse)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    db_client = Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@app.get("/invoices", response_model=List[InvoiceResponse])
def read_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).all()

@app.post("/invoices", response_model=InvoiceResponse)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    db_invoice = Invoice(
        invoice_number=invoice.invoice_number,
        client_id=invoice.client_id,
        user_id=invoice.user_id,
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
