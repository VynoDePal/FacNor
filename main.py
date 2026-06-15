from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import connect, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schema/tables")
def schema_tables() -> dict[str, list[str]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return {"tables": [row["name"] for row in rows]}
