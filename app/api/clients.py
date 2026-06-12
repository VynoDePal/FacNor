from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Client, Invoice, InvoiceLine
from app.schemas.schemas import ClientCreate, ClientResponse, InvoiceCreate, InvoiceResponse
from app.api.deps import get_current_user
from app.models.models import User

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("/", response_model=list[ClientResponse])
def read_clients(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Clients are global according to the provided schema.sql
    return db.query(Client).all()

@router.post("/", response_model=ClientResponse)
def create_client(
    client: ClientCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    db_client = Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client
