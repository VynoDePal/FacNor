from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from sqlalchemy import text

from fastapi.security import OAuth2PasswordRequestForm
from app.auth import (
    create_access_token, 
    verify_password, 
    get_current_user,
    get_password_hash
)
from app.models import User

app = FastAPI(title="FacNor API")

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
