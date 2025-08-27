"""Tests for user endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.core.security import create_access_token


@pytest.mark.unit
class TestUsers:
    """Test user endpoints."""

    def test_get_current_user_me(self, client: TestClient):
        """Test getting current user information."""
        # First register and login to get token
        user_data = {
            "email": "me@example.com",
            "username": "meuser",
            "password": "mepass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Get current user info
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]

    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_update_current_user(self, client: TestClient):
        """Test updating current user information."""
        # First register and login to get token
        user_data = {
            "email": "update@example.com",
            "username": "updateuser",
            "password": "updatepass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Update user info
        update_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = client.put("/api/v1/users/me", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["bio"] == update_data["bio"]

    def test_get_user_by_id(self, client: TestClient):
        """Test getting user by ID."""
        # First register and login to get token
        user_data = {
            "email": "getbyid@example.com",
            "username": "getbyiduser",
            "password": "getbyidpass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Get user by ID (assuming user ID is 1)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/1", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]

    def test_get_user_not_found(self, client: TestClient):
        """Test getting non-existent user."""
        # First register and login to get token
        user_data = {
            "email": "notfound@example.com",
            "username": "notfounduser",
            "password": "notfoundpass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Try to get non-existent user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/999", headers=headers)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
