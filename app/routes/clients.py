from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.client import Client as ClientModel
from app.schemas.client import Client, ClientCreate, ClientUpdate, ClientBase

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.post("/", response_model=Client, status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    db_client = ClientModel(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.get("/", response_model=List[Client])
def read_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(ClientModel).offset(skip).limit(limit).all()

@router.get("/{client_id}", response_model=Client)
def read_client(client_id: int, db: Session = Depends(get_db)):
    db_client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@router.put("/{client_id}", response_model=Client)
def update_client(client_id: int, client_update: ClientUpdate, db: Session = Depends(get_db)):
    db_client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_client, key, value)
    
    # Re-validate the client after update to ensure 'entreprise' requirements are still met
    try:
        Client.model_validate(db_client)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    db.commit()
    db.refresh(db_client)
    return db_client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    db_client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(db_client)
    db.commit()
    return None
