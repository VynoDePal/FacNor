from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.database import connect

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.getenv("FACNOR_JWT_SECRET", "facnor-development-secret")
JWT_EXPIRATION_MINUTES = int(os.getenv("FACNOR_JWT_EXPIRATION_MINUTES", "60"))
PASSWORD_ITERATIONS = 210_000


class UserRegistration(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str | None = None
    company_name: str | None = None
    company_siren: str | None = None
    company_vat_number: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("Invalid email address")
        return email

    @field_validator("full_name", "company_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str
    company_name: str
    company_siren: str | None = None
    company_vat_number: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


def _base64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _base64url_decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_base64url_encode(salt)}${_base64url_encode(derived_key)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _base64url_decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(_base64url_encode(derived_key), expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRATION_MINUTES)).timestamp()),
    }
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    signing_input = ".".join(
        [
            _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
        signing_input = f"{header_segment}.{payload_segment}"
        expected_signature = hmac.new(
            JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_base64url_encode(expected_signature), signature_segment):
            raise ValueError("Invalid token signature")
        header = json.loads(_base64url_decode(header_segment))
        payload = json.loads(_base64url_decode(payload_segment))
        if header.get("alg") != JWT_ALGORITHM:
            raise ValueError("Unsupported token algorithm")
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Expired token")
        return payload
    except (ValueError, json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def user_from_row(row: sqlite3.Row) -> UserPublic:
    return UserPublic(
        id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        company_name=row["company_name"],
        company_siren=row["company_siren"],
        company_vat_number=row["company_vat_number"],
    )


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_current_user(authorization: str | None = Header(default=None)) -> UserPublic:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(authorization.split(" ", 1)[1])
    user = get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user_from_row(user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(registration: UserRegistration) -> TokenResponse:
    password_hash = hash_password(registration.password)
    try:
        with connect() as connection:
            user_id = connection.execute(
                """
                INSERT INTO users (
                    email, password_hash, full_name, company_name, company_siren, company_vat_number
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    registration.email,
                    password_hash,
                    registration.full_name or registration.email.split("@", 1)[0],
                    registration.company_name or "FacNor",
                    registration.company_siren,
                    registration.company_vat_number,
                ),
            ).lastrowid
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = user_from_row(row)
    return TokenResponse(
        access_token=create_access_token(user.id, user.email),
        expires_in=JWT_EXPIRATION_MINUTES * 60,
        user=user,
    )


@router.post("/login", response_model=TokenResponse)
def login_user(credentials: UserLogin) -> TokenResponse:
    row = get_user_by_email(credentials.email)
    if row is None or not verify_password(credentials.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = user_from_row(row)
    return TokenResponse(
        access_token=create_access_token(user.id, user.email),
        expires_in=JWT_EXPIRATION_MINUTES * 60,
        user=user,
    )


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user
