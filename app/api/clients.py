from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_user
from app.api.schemas import ClientCreate, ClientUpdate, ClientOut
from app.services import client as client_service
from app.models.user import User

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_in: ClientCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return await client_service.create_client(db, client_in, current_user.id)

@router.get("/", response_model=List[ClientOut])
async def list_clients(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return await client_service.get_clients(db, current_user.id, skip, limit)

@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    client = await client_service.get_client(db, client_id, current_user.id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: UUID, 
    client_in: ClientUpdate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    client = await client_service.update_client(db, client_id, client_in, current_user.id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    success = await client_service.delete_client(db, client_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return None
