from fastapi import FastAPI
from app.api import auth
from app.api.deps import get_current_user
from app.api import clients

from fastapi import Depends

app = FastAPI(title="FacNor API")

app.include_router(clients.router)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

@app.get("/protected", tags=["Testing"])
async def protected_route(current_user=Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}, you are authenticated!"}

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}
