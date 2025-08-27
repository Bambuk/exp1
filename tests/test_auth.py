"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.core.security import create_access_token


@pytest.mark.unit
class TestAuth:
    """Test authentication endpoints."""

    def test_register_user(self, client: TestClient):
        """Test user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "newpassword123"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["full_name"] == user_data["full_name"]
        assert "password" not in data

    def test_register_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email."""
        user_data = {
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "password123"
        }
        
        # Register first user
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Try to register with same email
        user_data["username"] = "user2"
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_duplicate_username(self, client: TestClient):
        """Test registration with duplicate username."""
        user_data = {
            "email": "user1@example.com",
            "username": "duplicate",
            "password": "password123"
        }
        
        # Register first user
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Try to register with same username
        user_data["email"] = "user2@example.com"
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_login_success(self, client: TestClient):
        """Test successful login."""
        # First register a user
        user_data = {
            "email": "login@example.com",
            "username": "loginuser",
            "password": "loginpass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        # Then login
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_refresh_token(self, client: TestClient):
        """Test token refresh."""
        # First register and login to get tokens
        user_data = {
            "email": "refresh@example.com",
            "username": "refreshuser",
            "password": "refreshpass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(f"/api/v1/auth/refresh?refresh_token={refresh_token}")
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
