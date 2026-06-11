from fastapi import FastAPI, Depends, HTTPException
from fastapi import status as fastapi_status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import init_db, get_db
from app.models.user import User
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.schemas.invoice import InvoiceCreate
from app.schemas.invoice_read import InvoiceRead
from app.services.calculator import InvoiceCalculator
from app.services.numbering import InvoiceNumberingService
from app.services.invoice_service import InvoiceService
from app.schemas.client import ClientCreate, ClientUpdate, ClientRead
from app.schemas.auth import UserCreate, UserRead, Token
from app.services.auth_service import AuthService
from fastapi import Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from fastapi.staticfiles import StaticFiles


app = FastAPI(title="FacNor API")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def on_startup():
    init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to FacNor API", "status": "running"}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    token_data = AuthService.decode_access_token(token)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.post("/auth/register", response_model=UserRead, status_code=fastapi_status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = AuthService.get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not AuthService.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=fastapi_status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = AuthService.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/invoices/", response_model=List[InvoiceRead])
async def list_invoices(
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if status:
        query = query.filter(Invoice.status == status)
    
    # Use joinedload to avoid N+1 problem when accessing invoice.items in format_invoice_response
    from sqlalchemy.orm import joinedload
    invoices = query.options(joinedload(Invoice.items)).all()
    
    return [InvoiceService.format_invoice_response(inv) for inv in invoices]


@app.post("/invoices/", response_model=InvoiceRead, status_code=fastapi_status.HTTP_201_CREATED)
async def create_invoice(invoice_data: InvoiceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    # 1. Generate sequential number
    invoice_number = InvoiceNumberingService.generate_next_number(db, current_user.id)
    
    # 2. Create invoice
    db_invoice = Invoice(
        user_id=current_user.id,
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
    
    # 4. Calculate totals and format response
    return InvoiceService.format_invoice_response(db_invoice)

@app.get("/invoices/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    

@app.get("/clients/", response_model=List[ClientRead])
async def list_clients(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Client).filter(Client.user_id == current_user.id).all()

@app.post("/clients/", response_model=ClientRead, status_code=fastapi_status.HTTP_201_CREATED)
async def create_client(client_data: ClientCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_client = Client(user_id=current_user.id, **client_data.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@app.get("/clients/{client_id}", response_model=ClientRead)
async def get_client(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@app.put("/clients/{client_id}", response_model=ClientRead)
async def update_client(client_id: int, client_data: ClientUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    for key, value in client_data.model_dump(exclude_unset=True).items():
        setattr(db_client, key, value)
    
    db.commit()
    db.refresh(db_client)
    return db_client

@app.delete("/clients/{client_id}", status_code=fastapi_status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(db_client)
    db.commit()
    return None
