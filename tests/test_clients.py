import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app
from app.api.schemas import ClientOut
from uuid import uuid4

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
def mock_user_id():
    return uuid4()

@pytest.fixture
def mock_token():
    return "fake-token"

@pytest.mark.asyncio
async def test_create_client_unauthenticated(client):
    response = await client.post("/clients/", json={
        "client_type": "B2B",
        "name": "Test Company",
        "email": "test@company.com"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_clients_unauthenticated(client):
    response = await client.get("/clients/")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_client_unauthenticated(client):
    response = await client.get(f"/clients/{uuid4()}")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_client_unauthenticated(client):
    response = await client.put(f"/clients/{uuid4()}", json={"name": "Updated Name"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_delete_client_unauthenticated(client):
    response = await client.delete(f"/clients/{uuid4()}")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_client_crud_authenticated():
    """
    This test mocks the authentication and the service layer to verify the API endpoints.
    """
    user_id = uuid4()
    client_id = uuid4()
    
    mock_client_data = {
        "id": client_id,
        "user_id": user_id,
        "client_type": "B2B",
        "name": "Test Client",
        "email": "test@client.com",
        "phone": "123456789",
        "address": "123 Test St",
        "vat_number": "FR123456789",
    }

    # Use dependency overrides for authentication and DB
    from app.db.session import get_db
    from app.api.deps import get_current_user
    
    mock_user = AsyncMock()
    mock_user.id = user_id
    mock_user.username = "testuser"

    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch("app.services.client.get_clients", new_callable=AsyncMock) as mock_get_all, \
             patch("app.services.client.get_client", new_callable=AsyncMock) as mock_get_one, \
             patch("app.services.client.create_client", new_callable=AsyncMock) as mock_create, \
             patch("app.services.client.update_client", new_callable=AsyncMock) as mock_update, \
             patch("app.services.client.delete_client", new_callable=AsyncMock) as mock_delete:
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                ac.headers.update({"Authorization": "Bearer fake-token"})
                
                # Test Create
                create_payload = {
                    "client_type": "B2B",
                    "name": "Test Client",
                    "email": "test@client.com"
                }
                mock_create.return_value = mock_client_data
                response = await ac.post("/clients/", json=create_payload)
                assert response.status_code == 201
                assert response.json()["name"] == "Test Client"
                
                # Test List
                mock_get_all.return_value = [mock_client_data]
                response = await ac.get("/clients/")
                assert response.status_code == 200
                assert len(response.json()) == 1
                
                # Test Get
                mock_get_one.return_value = mock_client_data
                response = await ac.get(f"/clients/{client_id}")
                assert response.status_code == 200
                assert response.json()["id"] == str(client_id)
                
                # Test Update
                update_payload = {"name": "Updated Client Name"}
                mock_update.return_value = {**mock_client_data, "name": "Updated Client Name"}
                response = await ac.put(f"/clients/{client_id}", json=update_payload)
                assert response.status_code == 200
                assert response.json()["name"] == "Updated Client Name"
                
                # Test Delete
                mock_delete.return_value = True
                response = await ac.delete(f"/clients/{client_id}")
                assert response.status_code == 204
                
                # Test Get Not Found
                mock_get_one.return_value = None
                response = await ac.get(f"/clients/{client_id}")
                assert response.status_code == 404
    finally:
        app.dependency_overrides = {}
