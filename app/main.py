from fastapi import FastAPI
from app.core.database import init_db
from app.models.user import User
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem

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
