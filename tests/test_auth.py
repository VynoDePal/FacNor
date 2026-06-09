import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.models import User

# Create a new database for tests
# Using SQLite in memory for tests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_facnor.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def setup_module(module):
    Base.metadata.create_all(bind=test_engine)

def teardown_module(module):
    Base.metadata.drop_all(bind=test_engine)

# Override the get_db dependency
from app.api.dependencies import get_db # wait, get_db is in app.core.database
from app.core.database import get_db

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_register_user():
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "testpassword"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_register_duplicate_user():
    # User already registered in previous test
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "testpassword"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"

def test_login_success():
    # User exists from previous tests
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    token = data["access_token"]

    # Test protected route /me
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

def test_login_failure():
    response = client.post(
        "/auth/login",
        data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_access_protected_route_without_token():
    response = client.get("/me")
    assert response.status_code == 401
