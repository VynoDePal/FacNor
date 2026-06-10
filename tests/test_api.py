import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal

# Create tables for testing
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}

from app.database import get_db # Import needed for override

def test_db_connection_failure():
    # To test failure, we can temporarily override the get_db dependency
    from app.main import app
    from fastapi import Depends
    from unittest.mock import MagicMock

    def override_get_db():
        # Create a mock session that raises an exception when execute is called
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Mock connection failure")
        return mock_session

    app.dependency_overrides[get_db] = override_get_db
    
    response = client.get("/health")
    assert response.status_code == 503
    assert "Database connection failed" in response.json()["detail"]
    
    # Clean up overrides
    app.dependency_overrides.clear()

from app.database import get_db # Import needed for override
