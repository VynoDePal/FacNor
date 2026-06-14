from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth import router as auth_router
from app.database import get_connection, init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    with get_connection() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"service": "FacNor API", "status": "ok"}
