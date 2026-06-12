from fastapi import FastAPI
from app.core.database import engine
from app.api import auth, clients, invoices
from contextlib import asynccontextmanager
import sqlite3

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database using schema.sql to ensure consistency between tests and production
    with open("schema.sql", "r") as f:
        schema = f.read()
    
    db_path = engine.url.database
    with sqlite3.connect(db_path) as sqlite_conn:
        sqlite_conn.executescript(schema)
    yield

app = FastAPI(title="FacNor API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(invoices.router)
