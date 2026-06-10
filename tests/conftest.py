import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db
import os

# Import models to ensure they are registered with Base.metadata
from app.models.user import User
from app.models.client import Client
from app.models.facture import Facture, LigneFacture

from app.models.sequence import Sequence

# Use a file-based database for testing to avoid issues with in-memory SQLite and connection pooling
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_facnor.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables
    Base.metadata.drop_all(bind=engine)

# Remove the duplicate imports and redefined overrides at the end of the file

@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

