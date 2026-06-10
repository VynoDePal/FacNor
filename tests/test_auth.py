import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db
import os

# Database setup is now handled in conftest.py


client = TestClient(app)

# Database setup is now handled in conftest.py


def test_register_user():
    response = client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "testuser"

def test_register_duplicate_user():
    client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpassword"}
    )
    response = client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 400

def test_login_success():
    client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpassword"}
    )
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure():
    client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpassword"}
    )
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_protected_route_unauthenticated():
    # We need a protected route to test 401
    # Let's add a temporary protected route to the app for testing
    from app.core.security import get_current_user
    from fastapi import Depends

    @app.get("/test-protected")
    async def protected_endpoint(current_user=Depends(get_current_user)):
        return {"message": "protected"}

    response = client.get("/test-protected")
    assert response.status_code == 401

def test_protected_route_authenticated():
    from app.core.security import get_current_user
    from fastapi import Depends

    @app.get("/test-protected")
    async def protected_endpoint(current_user=Depends(get_current_user)):
        return {"message": "protected"}

    client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpassword"}
    )
    login_response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    token = login_response.json()["access_token"]
    
    response = client.get(
        "/test-protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "protected"
