from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from sqlalchemy import text
from . import crud, schemas
from typing import Optional, List
from datetime import datetime

from . import crud, schemas
from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordRequestForm
from app.auth import (
    create_access_token, 
    verify_password, 
    get_current_user,
    get_password_hash
)
from app.models import User

app = FastAPI(title="FacNor API")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FacNor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=None)
async def create_user(user_data: dict, db: Session = Depends(get_db)):
    # Simplified user creation for demo/testing purposes
    db_user = User(
        username=user_data['username'],
        email=user_data['email'],
        hashed_password=get_password_hash(user_data['password'])
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "username": db_user.username, "email": db_user.email}

@app.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Simple query to verify database connection
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/clients/", response_model=schemas.Client, status_code=201)
def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    return crud.create_client(db=db, client=client)

@app.get("/clients/", response_model=list[schemas.Client])
def read_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_clients(db, skip=skip, limit=limit)

@app.get("/clients/{client_id}", response_model=schemas.Client)
def read_client(client_id: int, db: Session = Depends(get_db)):
    db_client = crud.get_client(db, client_id=client_id)
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@app.put("/clients/{client_id}", response_model=schemas.Client)
def update_client(client_id: int, client: schemas.ClientUpdate, db: Session = Depends(get_db)):
    db_client = crud.update_client(db, client_id=client_id, client=client)
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@app.delete("/clients/{client_id}", status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    success = crud.delete_client(db, client_id=client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return None
@app.get("/invoices/", response_model=list[schemas.Invoice])
def read_invoices(
    skip: int = 0, 
    limit: int = 100, 
    client_id: Optional[int] = None, 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return crud.get_invoices(db, user_id=current_user.id, skip=skip, limit=limit, client_id=client_id, start_date=start_date, end_date=end_date)

@app.post("/invoices/", response_model=schemas.Invoice, status_code=201)
def create_invoice(invoice: schemas.InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.create_invoice(db=db, invoice=invoice, user_id=current_user.id)

@app.get("/invoices/{invoice_id}", response_model=schemas.Invoice)
def read_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_invoice = crud.get_invoice(db, invoice_id=invoice_id, user_id=current_user.id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@app.put("/invoices/{invoice_id}", response_model=schemas.Invoice)
def update_invoice(invoice_id: int, invoice: schemas.InvoiceUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_invoice = crud.update_invoice(db, invoice_id=invoice_id, invoice_update=invoice, user_id=current_user.id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@app.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    success = crud.delete_invoice(db, invoice_id=invoice_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return None

