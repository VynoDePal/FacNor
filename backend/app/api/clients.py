from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.client import Client, ClientType
from backend.app.schemas.client import (
    COMPANY_IDENTITY_REQUIRED_MESSAGE,
    ClientCreate,
    ClientRead,
    ClientUpdate,
    validate_company_identity,
)

router = APIRouter(prefix="/clients", tags=["clients"])


def _get_client_or_404(client_id: int, db: Session) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")
    return client


def _validate_company_identity(client: Client) -> None:
    try:
        validate_company_identity(client.type, client.siren, client.vat_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=COMPANY_IDENTITY_REQUIRED_MESSAGE) from exc


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)) -> Client:
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("", response_model=list[ClientRead])
def list_clients(
    db: Session = Depends(get_db),
    client_type: ClientType | None = Query(default=None, alias="type"),
    search: str | None = Query(default=None, min_length=1),
) -> list[Client]:
    statement = select(Client).order_by(Client.name.asc(), Client.id.asc())
    if client_type is not None:
        statement = statement.where(Client.type == client_type)
    if search:
        statement = statement.where(Client.name.ilike(f"%{search}%"))
    return list(db.scalars(statement).all())


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: Session = Depends(get_db)) -> Client:
    return _get_client_or_404(client_id, db)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(client_id: int, payload: ClientUpdate, db: Session = Depends(get_db)) -> Client:
    client = _get_client_or_404(client_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    _validate_company_identity(client)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)) -> None:
    client = _get_client_or_404(client_id, db)
    db.delete(client)
    db.commit()
