from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.routes import auth
import sqlite3
import os

app = FastAPI(title="FacNor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.on_event("startup")
def startup():
    # Initialize database using schema.sql
    schema_path = "schema.sql"
    if os.path.exists(schema_path):
        with sqlite3.connect("facnor.db") as conn:
            with open(schema_path, "r") as f:
                conn.executescript(f.read())
            conn.commit()

@app.get("/")
async def root():
    return {"message": "Welcome to FacNor API", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
