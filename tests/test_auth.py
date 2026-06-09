import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import engine, Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Mocking the DB session for testing
# In a real scenario, we'd use a test database
# For this task, we can use an in-memory SQLite if we don't have Postgres running, 
# but since the requirements specify Postgres and the schema is PG specific, 
# we should ideally have a test DB.
# However, for verifying the 401 behavior (unauthenticated access), 
# we don't even need the DB to be fully operational for the protected route's initial check.

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_protected_route_unauthenticated(client):
    """Verify that a request to a protected route without a token returns 401."""
    response = await client.get("/protected")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated" # FastAPI OAuth2PasswordBearer default detail

@pytest.mark.asyncio
async def test_health_check(client):
    """Verify that the health check route is accessible."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
