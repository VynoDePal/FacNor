from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.auth import UserResponse, get_current_user
from app.database import get_connection

router = APIRouter(prefix="/clients", tags=["clients"])

ClientType = Literal["individual", "company"]


class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client_type: ClientType
    email: EmailStr | None = None
    address: str | None = None
    siren: str | None = None
    vat_number: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    client_type: ClientType | None = None
    email: EmailStr | None = None
    address: str | None = None
    siren: str | None = None
    vat_number: str | None = None


class ClientResponse(ClientBase):
    id: int
    user_id: int
    created_at: str


_DIGITS_RE = re.compile(r"\D+")
_VAT_RE = re.compile(r"^FR(\d{2})(\d{9})$")


def _normalize_siren(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _DIGITS_RE.sub("", value)
    return normalized or None


def _normalize_vat_number(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[\s.\-]+", "", value).upper()
    return normalized or None


def _is_valid_luhn(value: str) -> bool:
    total = 0
    double_digit = False
    for character in reversed(value):
        digit = int(character)
        if double_digit:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
        double_digit = not double_digit
    return total % 10 == 0


def _expected_french_vat_key(siren: str) -> str:
    return f"{(12 + 3 * (int(siren) % 97)) % 97:02d}"


def _validate_client_payload(payload: ClientBase | ClientUpdate, current: dict | None = None) -> dict:
    data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    merged = dict(current or {})
    merged.update(data)

    if "siren" in data:
        merged["siren"] = _normalize_siren(data.get("siren"))
    if "vat_number" in data:
        merged["vat_number"] = _normalize_vat_number(data.get("vat_number"))

    client_type = merged.get("client_type")
    siren = merged.get("siren")
    vat_number = merged.get("vat_number")

    if client_type == "company":
        if not siren:
            raise HTTPException(status_code=422, detail="Le SIREN est obligatoire pour une entreprise.")
        if not vat_number:
            raise HTTPException(status_code=422, detail="Le numéro de TVA est obligatoire pour une entreprise.")
    elif client_type == "individual":
        siren = None
        vat_number = None
        merged["siren"] = None
        merged["vat_number"] = None

    if siren is not None:
        if len(siren) != 9 or not _is_valid_luhn(siren):
            raise HTTPException(status_code=422, detail="Le SIREN doit contenir 9 chiffres valides.")

    if vat_number is not None:
        match = _VAT_RE.fullmatch(vat_number)
        if match is None:
            raise HTTPException(status_code=422, detail="Le numéro de TVA doit respecter le format FR + clé + SIREN.")
        vat_key, vat_siren = match.groups()
        if siren is not None and vat_siren != siren:
            raise HTTPException(status_code=422, detail="Le numéro de TVA doit correspondre au SIREN.")
        if not _is_valid_luhn(vat_siren) or vat_key != _expected_french_vat_key(vat_siren):
            raise HTTPException(status_code=422, detail="Le numéro de TVA intracommunautaire est invalide.")

    return merged


def _client_response(row) -> ClientResponse:
    return ClientResponse(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        client_type=row["client_type"],
        email=row["email"],
        address=row["address"],
        siren=row["siren"],
        vat_number=row["vat_number"],
        created_at=row["created_at"],
    )


def _get_client_row(client_id: int, user_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, user_id, name, client_type, email, address, siren, vat_number, created_at
            FROM clients
            WHERE id = ? AND user_id = ?
            """,
            (client_id, user_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable.")
    return row


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> ClientResponse:
    data = _validate_client_payload(payload)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO clients (user_id, name, client_type, email, address, siren, vat_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                data["name"],
                data["client_type"],
                data.get("email"),
                data.get("address"),
                data.get("siren"),
                data.get("vat_number"),
            ),
        )
        row = connection.execute(
            """
            SELECT id, user_id, name, client_type, email, address, siren, vat_number, created_at
            FROM clients
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _client_response(row)


@router.get("", response_model=list[ClientResponse])
def list_clients(current_user: UserResponse = Depends(get_current_user)) -> list[ClientResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, name, client_type, email, address, siren, vat_number, created_at
            FROM clients
            WHERE user_id = ?
            ORDER BY id
            """,
            (current_user.id,),
        ).fetchall()
    return [_client_response(row) for row in rows]


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> ClientResponse:
    return _client_response(_get_client_row(client_id, current_user.id))


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> ClientResponse:
    current = dict(_get_client_row(client_id, current_user.id))
    data = _validate_client_payload(payload, current=current)
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE clients
            SET name = ?, client_type = ?, email = ?, address = ?, siren = ?, vat_number = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                data["name"],
                data["client_type"],
                data.get("email"),
                data.get("address"),
                data.get("siren"),
                data.get("vat_number"),
                client_id,
                current_user.id,
            ),
        )
        row = connection.execute(
            """
            SELECT id, user_id, name, client_type, email, address, siren, vat_number, created_at
            FROM clients
            WHERE id = ? AND user_id = ?
            """,
            (client_id, current_user.id),
        ).fetchone()
    return _client_response(row)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    _get_client_row(client_id, current_user.id)
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM clients WHERE id = ? AND user_id = ?",
            (client_id, current_user.id),
        )
