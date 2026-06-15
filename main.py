from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.database import connect, init_db
from app.invoices import router as invoices_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FacNor API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "FacNor API"}

app.include_router(auth_router)
app.include_router(invoices_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


REQUIRED_TABLES = {"users", "clients", "invoice_sequences", "invoices", "invoice_lines"}


def list_application_tables() -> list[str]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [row["name"] for row in rows]


@app.get("/health/db")
def database_health() -> dict[str, bool | list[str]]:
    tables = list_application_tables()
    return {"status": REQUIRED_TABLES.issubset(tables), "tables": tables}


@app.get("/schema/tables")
def schema_tables() -> dict[str, list[str]]:
    return {"tables": list_application_tables()}
