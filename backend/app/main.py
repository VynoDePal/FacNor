from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", tags=["health"])
def api_healthcheck() -> dict[str, str]:
    return healthcheck()


@app.get("/healthcheck", tags=["health"])
def healthcheck_alias() -> dict[str, str]:
    return healthcheck()


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"message": "FacNor API", "status": "ok"}
