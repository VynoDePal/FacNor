from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.clients import router as clients_router
from app.database import get_connection, init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FACNOR_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(clients_router)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    with get_connection() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"service": "FacNor API", "status": "ok"}
