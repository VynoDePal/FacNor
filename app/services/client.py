from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from uuid import UUID
from typing import List, Optional
from app.models.client import Client
from app.api.schemas import ClientCreate, ClientUpdate

async def get_clients(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Client]:
    result = await db.execute(
        select(Client).where(Client.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()

async def get_client(db: AsyncSession, client_id: UUID, user_id: UUID) -> Optional[Client]:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def create_client(db: AsyncSession, client_data: ClientCreate, user_id: UUID) -> Client:
    db_client = Client(**client_data.model_dump(), user_id=user_id)
    db.add(db_client)
    await db.commit()
    await db.refresh(db_client)
    return db_client

async def update_client(db: AsyncSession, client_id: UUID, client_data: ClientUpdate, user_id: UUID) -> Optional[Client]:
    # Check if client exists and belongs to user
    client = await get_client(db, client_id, user_id)
    if not client:
        return None
    
    update_data = client_data.model_dump(exclude_unset=True)
    if update_data:
        await db.execute(
            update(Client).where(Client.id == client_id).values(**update_data)
        )
        await db.commit()
        await db.refresh(client)
    
    return client

async def delete_client(db: AsyncSession, client_id: UUID, user_id: UUID) -> bool:
    client = await get_client(db, client_id, user_id)
    if not client:
        return False
    
    await db.execute(
        delete(Client).where(Client.id == client_id, Client.user_id == user_id)
    )
    await db.commit()
    return True
