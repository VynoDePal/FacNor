from fastapi import FastAPI
from app.core.database import engine, Base
from app.models import models
from app.api import auth, clients
from app.api.dependencies import get_current_user
from fastapi import Depends

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FacNor API")

app.include_router(auth.router)
app.include_router(clients.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to FacNor API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/me")
def read_users_me(current_user=Depends(get_current_user)):
    return {"username": current_user.username, "email": current_user.email}
