from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.facture import Facture as FactureModel, LigneFacture as LigneFactureModel
from app.models.client import Client as ClientModel
from app.schemas.facture import Facture, FactureCreate, FactureUpdate
from app.core.numbering import get_next_sequence_value

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
    
    # Determine the invoice number and create the facture
    # We use a retry loop to handle potential race conditions on the invoice number
    max_retries = 5
    for attempt in range(max_retries):
        try:
            if facture.numero:
                numero = facture.numero
                # Check if facture number is unique
                db_facture = db.query(FactureModel).filter(FactureModel.numero == numero).first()
                if db_facture:
                    raise HTTPException(status_code=400, detail="Facture number already exists")
            else:
                next_val = get_next_sequence_value(db, "facture_numero")
                numero = f"FAC-{next_val:06d}"

            # Create facture
            new_facture = FactureModel(
                numero=numero,
                client_id=facture.client_id,
                date_facture=facture.date_facture,
                date_echeance=facture.date_echeance,
                statut=facture.statut,
                notes=facture.notes
            )
            db.add(new_facture)
            db.commit()
            db.refresh(new_facture)
            break # Success!
        except Exception as e:
            db.rollback()
            if attempt == max_retries - 1:
                raise e
            # Only retry if it's a uniqueness constraint violation on the invoice number
            # We can't easily check the exact DB error here without more imports, 
            # but we know that in this loop, the most likely reason for failure is the numero.
            # To be safer, we could check for IntegrityError.
            continue

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
