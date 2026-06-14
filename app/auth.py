from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from app.database import get_connection

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000
SESSION_TTL_DAYS = 7

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return (
        f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = hashed_password.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(expected.hex(), digest_hex)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _format_datetime(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = _format_datetime(_utcnow() + timedelta(days=SESSION_TTL_DAYS))
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
            """,
            (user_id, token, expires_at),
        )
    return token


def _user_response(row) -> UserResponse:
    return UserResponse(id=row["id"], email=row["email"], full_name=row["full_name"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> TokenResponse:
    hashed_password = hash_password(payload.password)
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (email, full_name, hashed_password)
                VALUES (?, ?, ?)
                """,
                (payload.email.lower(), payload.full_name, hashed_password),
            )
            user_id = cursor.lastrowid
            user = connection.execute(
                "SELECT id, email, full_name FROM users WHERE id = ?", (user_id,)
            ).fetchone()
    except Exception as exc:
        if "UNIQUE constraint failed: users.email" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un utilisateur existe déjà avec cet email.",
            ) from exc
        raise

    token = _create_session(user["id"])
    return TokenResponse(access_token=token, user=_user_response(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, email, full_name, hashed_password FROM users WHERE email = ?",
            (payload.email.lower(),),
        ).fetchone()

    if user is None or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe invalide.",
        )

    token = _create_session(user["id"])
    return TokenResponse(access_token=token, user=_user_response(user))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification manquant.",
        )

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.email, users.full_name
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (credentials.credentials, _format_datetime(_utcnow())),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification invalide ou expiré.",
        )

    return _user_response(row)


@router.get("/me", response_model=UserResponse)
def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
