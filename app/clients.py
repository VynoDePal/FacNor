from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator, model_validator

from app.auth import UserPublic, get_current_user
from app.database import connect

router = APIRouter(prefix="/clients", tags=["clients"])
ClientType = Literal["B2B", "B2C"]


class ClientBase(BaseModel):
    client_type: ClientType
    name: str = Field(min_length=1)
    email: str | None = None
    phone: str | None = None
    address_line1: str = Field(min_length=1)
    address_line2: str | None = None
    postal_code: str = Field(min_length=1)
    city: str = Field(min_length=1)
    country: str = Field(default="France", min_length=1)
    siren: str | None = None
    vat_number: str | None = None
    contact_full_name: str | None = None

    @field_validator(
        "name",
        "email",
        "phone",
        "address_line1",
        "address_line2",
        "postal_code",
        "city",
        "country",
        "siren",
        "vat_number",
        "contact_full_name",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and ("@" not in value or value.startswith("@") or value.endswith("@")):
            raise ValueError("Invalid email address")
        return value

    @field_validator("siren")
    @classmethod
    def validate_siren_format(cls, value: str | None) -> str | None:
        if value is not None and (len(value) != 9 or not value.isdigit()):
            raise ValueError("SIREN must contain 9 digits")
        return value

    @model_validator(mode="after")
    def validate_client_type_rules(self) -> "ClientBase":
        if self.client_type == "B2B" and self.siren is None:
            raise ValueError("B2B clients must provide a SIREN")
        if self.client_type == "B2C" and (self.siren is not None or self.vat_number is not None):
            raise ValueError("B2C clients cannot provide SIREN or VAT number")
        return self


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    client_type: ClientType | None = None
    name: str | None = Field(default=None, min_length=1)
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = Field(default=None, min_length=1)
    address_line2: str | None = None
    postal_code: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1)
    siren: str | None = None
    vat_number: str | None = None
    contact_full_name: str | None = None

    @field_validator(
        "name",
        "email",
        "phone",
        "address_line1",
        "address_line2",
        "postal_code",
        "city",
        "country",
        "siren",
        "vat_number",
        "contact_full_name",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return ClientBase.strip_text(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return ClientBase.validate_email(value)

    @field_validator("siren")
    @classmethod
    def validate_siren_format(cls, value: str | None) -> str | None:
        return ClientBase.validate_siren_format(value)


class ClientPublic(ClientBase):
    id: int
    user_id: int
    created_at: str
    updated_at: str


def _client_from_row(row: sqlite3.Row) -> ClientPublic:
    return ClientPublic(
        id=row["id"],
        user_id=row["user_id"],
        client_type=row["client_type"],
        name=row["name"],
        email=row["email"],
        phone=row["phone"],
        address_line1=row["address_line1"],
        address_line2=row["address_line2"],
        postal_code=row["postal_code"],
        city=row["city"],
        country=row["country"],
        siren=row["siren"],
        vat_number=row["vat_number"],
        contact_full_name=row["contact_full_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_client_row(connection: sqlite3.Connection, user_id: int, client_id: int) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM clients WHERE id = ? AND user_id = ?", (client_id, user_id)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return row


def _raise_integrity_error(error: sqlite3.IntegrityError) -> None:
    message = str(error).lower()
    if "unique" in message:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client already exists")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client data")


@router.post("", response_model=ClientPublic, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, current_user: UserPublic = Depends(get_current_user)) -> ClientPublic:
    try:
        with connect() as connection:
            client_id = connection.execute(
                """
                INSERT INTO clients (
                    user_id, client_type, name, email, phone, address_line1, address_line2,
                    postal_code, city, country, siren, vat_number, contact_full_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current_user.id,
                    payload.client_type,
                    payload.name,
                    payload.email,
                    payload.phone,
                    payload.address_line1,
                    payload.address_line2,
                    payload.postal_code,
                    payload.city,
                    payload.country,
                    payload.siren,
                    payload.vat_number,
                    payload.contact_full_name,
                ),
            ).lastrowid
            return _client_from_row(_get_client_row(connection, current_user.id, client_id))
    except sqlite3.IntegrityError as error:
        _raise_integrity_error(error)


@router.get("", response_model=list[ClientPublic])
def list_clients(current_user: UserPublic = Depends(get_current_user)) -> list[ClientPublic]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM clients WHERE user_id = ? ORDER BY name COLLATE NOCASE, id",
            (current_user.id,),
        ).fetchall()
    return [_client_from_row(row) for row in rows]


@router.get("/{client_id}", response_model=ClientPublic)
def read_client(client_id: int, current_user: UserPublic = Depends(get_current_user)) -> ClientPublic:
    with connect() as connection:
        return _client_from_row(_get_client_row(connection, current_user.id, client_id))


def _update_client(client_id: int, payload: ClientUpdate, current_user: UserPublic) -> ClientPublic:
    with connect() as connection:
        existing = _client_from_row(_get_client_row(connection, current_user.id, client_id))
        merged = existing.model_dump(exclude={"id", "user_id", "created_at", "updated_at"})
        merged.update(payload.model_dump(exclude_unset=True))
        validated = ClientCreate(**merged)
        try:
            connection.execute(
                """
                UPDATE clients
                SET client_type = ?, name = ?, email = ?, phone = ?, address_line1 = ?,
                    address_line2 = ?, postal_code = ?, city = ?, country = ?, siren = ?,
                    vat_number = ?, contact_full_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (
                    validated.client_type,
                    validated.name,
                    validated.email,
                    validated.phone,
                    validated.address_line1,
                    validated.address_line2,
                    validated.postal_code,
                    validated.city,
                    validated.country,
                    validated.siren,
                    validated.vat_number,
                    validated.contact_full_name,
                    client_id,
                    current_user.id,
                ),
            )
        except sqlite3.IntegrityError as error:
            _raise_integrity_error(error)
        return _client_from_row(_get_client_row(connection, current_user.id, client_id))


@router.put("/{client_id}", response_model=ClientPublic)
def replace_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: UserPublic = Depends(get_current_user),
) -> ClientPublic:
    return _update_client(client_id, payload, current_user)


@router.patch("/{client_id}", response_model=ClientPublic)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: UserPublic = Depends(get_current_user),
) -> ClientPublic:
    return _update_client(client_id, payload, current_user)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_client(client_id: int, current_user: UserPublic = Depends(get_current_user)) -> Response:
    with connect() as connection:
        _get_client_row(connection, current_user.id, client_id)
        try:
            connection.execute("DELETE FROM clients WHERE id = ? AND user_id = ?", (client_id, current_user.id))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client is used by invoices")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
