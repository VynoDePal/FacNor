from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.db.session import Base, engine
import app.models  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(title="FacNor API")
    Base.metadata.create_all(bind=engine)
    app.include_router(auth_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
