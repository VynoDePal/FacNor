import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from main import app
import sqlite3
import os

# Use a file-based database for tests to avoid in-memory connection issues with some FastAPI/SQLAlchemy setups
TEST_DATABASE_URL = "sqlite:///./test_facnor.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Create schema using schema.sql
    with open("schema.sql", "r") as f:
        schema = f.read()

    with engine.connect() as connection:
        connection.connection.executescript(schema)
    
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    yield
    # Cleanup after session
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_facnor.db"):
        os.remove("test_facnor.db")

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_header():
    """
    Fixture to provide an authentication header for a test user.
    """
    client = TestClient(app)
    # Register user
    client.post("/auth/register", json={
        "username": "testuser",
        "password": "testpassword",
        "email": "testuser@example.com"
    })
    # Login user
    response = client.post("/auth/login", data={
        "username": "testuser",
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
