from fastapi import FastAPI

from backend.app.api.clients import router as clients_router
from backend.app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FacNor API")
app.include_router(clients_router, prefix="/api")
