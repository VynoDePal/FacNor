import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User
from app.auth import get_password_hash

# Use an in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_facnor.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_user():
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpassword"}
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_auth_flow():
    # 1. Create a user
    user_data = {"username": "authuser", "email": "auth@example.com", "password": "authpassword"}
    client.post("/users/", json=user_data)

    # 2. Login to get token
    login_data = {"username": "authuser", "password": "authpassword"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]

    # 3. Access protected route /me
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "authuser"

def test_protected_route_no_token():
    response = client.get("/me")
    assert response.status_code == 401

def test_protected_route_invalid_token():
    response = client.get("/me", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401

def test_login_wrong_password():
    user_data = {"username": "wrongpass", "email": "wrong@example.com", "password": "correctpassword"}
    client.post("/users/", json=user_data)

    login_data = {"username": "wrongpass", "password": "wrongpassword"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 401
