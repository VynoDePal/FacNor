from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.facture import Facture as FactureModel, LigneFacture as LigneFactureModel
from app.models.client import Client as ClientModel
from app.schemas.facture import Facture, FactureCreate, FactureUpdate

router = APIRouter(
    prefix="/factures",
    tags=["factures"]
)

@router.post("/", response_model=Facture, status_code=status.HTTP_201_CREATED)
def create_facture(facture: FactureCreate, db: Session = Depends(get_db)):
    # Check if client exists
    client = db.query(ClientModel).filter(ClientModel.id == facture.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if facture number is unique
    db_facture = db.query(FactureModel).filter(FactureModel.numero == facture.numero).first()
    if db_facture:
        raise HTTPException(status_code=400, detail="Facture number already exists")

    # Create facture
    new_facture = FactureModel(
        numero=facture.numero,
        client_id=facture.client_id,
        date_facture=facture.date_facture,
        date_echeance=facture.date_echeance,
        statut=facture.statut,
        notes=facture.notes
    )
    db.add(new_facture)
    db.commit()
    db.refresh(new_facture)

    # Create lines
    for line_data in facture.lignes:
        db_line = LigneFactureModel(**line_data.model_dump())
        db_line.facture_id = new_facture.id
        db.add(db_line)
    
    db.commit()
    db.refresh(new_facture)
    return new_facture

@router.get("/", response_model=List[Facture])
def read_factures(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(FactureModel).offset(skip).limit(limit).all()

@router.get("/{facture_id}", response_model=Facture)
def read_facture(facture_id: int, db: Session = Depends(get_db)):
    db_facture = db.query(FactureModel).filter(FactureModel.id == facture_id).first()
    if not db_facture:
        raise HTTPException(status_code=404, detail="Facture not found")
    return db_facture

@router.put("/{facture_id}", response_model=Facture)
def update_facture(facture_id: int, facture_update: FactureUpdate, db: Session = Depends(get_db)):
    db_facture = db.query(FactureModel).filter(FactureModel.id == facture_id).first()
    if not db_facture:
        raise HTTPException(status_code=404, detail="Facture not found")
    
    update_data = facture_update.model_dump(exclude_unset=True)
    
    # Check if numero is being updated and if it's unique
    if "numero" in update_data:
        existing = db.query(FactureModel).filter(
            FactureModel.numero == update_data["numero"],
            FactureModel.id != facture_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Facture number already exists")

    # Check if client_id is being updated and if client exists
    if "client_id" in update_data:
        client = db.query(ClientModel).filter(ClientModel.id == update_data["client_id"]).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    for key, value in update_data.items():
        setattr(db_facture, key, value)
    
    db.commit()
    db.refresh(db_facture)
    return db_facture

@router.delete("/{facture_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_facture(facture_id: int, db: Session = Depends(get_db)):
    db_facture = db.query(FactureModel).filter(FactureModel.id == facture_id).first()
    if not db_facture:
        raise HTTPException(status_code=404, detail="Facture not found")
    db.delete(db_facture)
    db.commit()
    return None
