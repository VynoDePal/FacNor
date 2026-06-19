from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth import create_access_token, get_current_user, hash_password, verify_password
from backend.app.database import get_db, init_db
from backend.app.models import User


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str = Field(min_length=8)
    company_name: str = Field(min_length=1, max_length=255)
    siren: str | None = Field(default=None, min_length=9, max_length=9)
    vat_number: str | None = Field(default=None, max_length=32)
    address: str = Field(min_length=1)


class UserLogin(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str


class UserRead(BaseModel):
    id: int
    email: str
    company_name: str
    siren: str | None
    vat_number: str | None
    address: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead



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


@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register_user(payload: UserCreate, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    existing_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        company_name=payload.company_name,
        siren=payload.siren,
        vat_number=payload.vat_number,
        address=payload.address,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
def login_user(payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@app.get("/api/auth/me", response_model=UserRead, tags=["auth"])
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
