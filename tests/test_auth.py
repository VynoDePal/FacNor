import pytest
from app.core.security import get_password_hash
from app.models.models import User

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "testpassword"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_register_duplicate_user(client):
    # First register the user
    client.post(
        "/auth/register",
        json={"username": "dupuser", "email": "dup@example.com", "password": "password"}
    )
    # Now register the same user again
    response = client.post(
        "/auth/register",
        json={"username": "dupuser", "email": "dup@example.com", "password": "password"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"

def test_login_success(client):
    # Register a user first
    client.post(
        "/auth/register",
        json={"username": "loginuser", "email": "login@example.com", "password": "password"}
    )
    
    # Now login
    response = client.post(
        "/auth/login",
        data={"username": "loginuser", "password": "password"}
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
    assert response.json()["username"] == "loginuser"

def test_login_failure(client):
    response = client.post(
        "/auth/login",
        data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_access_protected_route_without_token(client):
    response = client.get("/me")
    assert response.status_code == 401
