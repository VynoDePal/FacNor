from fastapi import FastAPI
from app.core.database import engine, Base
from app.models import models

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FacNor API")

@app.get("/")
def read_root():
    return {"message": "Welcome to FacNor API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
