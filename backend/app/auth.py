import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User

TOKEN_TTL_HOURS = 24
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "facnor-development-secret")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, encoded_salt, encoded_digest = hashed_password.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False

    salt = base64.urlsafe_b64decode(encoded_salt.encode())
    expected_digest = base64.urlsafe_b64decode(encoded_digest.encode())
    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {"sub": str(user.id), "email": user.email, "exp": int(expires_at.timestamp())}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise _unauthorized()
    if credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.isdigit():
        raise _unauthorized()

    user = db.get(User, int(user_id))
    if user is None:
        raise _unauthorized()
    return user


def _decode_token(token: str) -> dict[str, Any]:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise _unauthorized() from exc

    if not hmac.compare_digest(_sign(encoded_payload), signature):
        raise _unauthorized()

    padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded_payload.encode()))
    except (json.JSONDecodeError, ValueError) as exc:
        raise _unauthorized() from exc

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(datetime.now(timezone.utc).timestamp()):
        raise _unauthorized()
    return payload


def _sign(value: str) -> str:
    return hmac.new(AUTH_SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
