import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, get_db, SessionLocal
from app.models.client import Client
from app.models.user import User

# Mock dependency for get_db
def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=SessionLocal().bind)
    # Create a test user
    db = SessionLocal()
    user = User(username="testuser", email="test@example.com", hashed_password="password")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate a token for the test user
    from app.services.auth_service import AuthService
    token = AuthService.create_access_token(data={"sub": user.username})
    
    yield token
    
    # Cleanup
    Base.metadata.drop_all(bind=SessionLocal().bind)

def test_create_client(setup_db):
    token = setup_db
    response = client.post(
        "/clients/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Client Test",
            "email": "client@test.com",
            "address": "123 Test St",
            "phone": "0123456789",
            "siren": "123456789",
            "vat_number": "FR123456789",
            "is_company": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Client Test"

def test_list_clients(setup_db):
    token = setup_db
    # Create a client
    db = SessionLocal()
    # We need a user_id to create the client in DB
    user = db.query(User).filter(User.username == "testuser").first()
    client_obj = Client(user_id=user.id, name="Client 1")
    db.add(client_obj)
    db.commit()
    
    response = client.get("/clients/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Client 1"

def test_get_client(setup_db):
    token = setup_db
    db = SessionLocal()
    user = db.query(User).filter(User.username == "testuser").first()
    client_obj = Client(user_id=user.id, name="Client 2")
    db.add(client_obj)
    db.commit()
    
    response = client.get(f"/clients/{client_obj.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "Client 2"

def test_update_client(setup_db):
    token = setup_db
    db = SessionLocal()
    user = db.query(User).filter(User.username == "testuser").first()
    client_obj = Client(user_id=user.id, name="Client 3")
    db.add(client_obj)
    db.commit()
    
    response = client.put(
        f"/clients/{client_obj.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Client 3 Updated"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Client 3 Updated"

def test_delete_client(setup_db):
    token = setup_db
    db = SessionLocal()
    user = db.query(User).filter(User.username == "testuser").first()
    client_obj = Client(user_id=user.id, name="Client 4")
    db.add(client_obj)
    db.commit()
    
    response = client.delete(f"/clients/{client_obj.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
    
    response = client.get(f"/clients/{client_obj.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
