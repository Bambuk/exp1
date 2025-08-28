"""Tests for user endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestUsers:
    """Test user endpoints."""

    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/users/me")
        # Should return 401 or 403 depending on middleware
        assert response.status_code in [401, 403]

    def test_get_user_by_id_unauthorized(self, client: TestClient):
        """Test getting user by ID without authentication."""
        response = client.get("/api/v1/users/1")
        # Should return 401 or 403 depending on middleware
        assert response.status_code in [401, 403]

    def test_update_current_user_unauthorized(self, client: TestClient):
        """Test updating current user without authentication."""
        update_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio"
        }
        response = client.put("/api/v1/users/me", json=update_data)
        # Should return 401 or 403 depending on middleware
        assert response.status_code in [401, 403]

    def test_get_users_list_unauthorized(self, client: TestClient):
        """Test getting users list without authentication."""
        response = client.get("/api/v1/users/")
        # Should return 401 or 403 depending on middleware
        assert response.status_code in [401, 403]

    def test_create_user_unauthorized(self, client: TestClient):
        """Test creating user without authentication."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123"
        }
        response = client.post("/api/v1/users/", json=user_data)
        # Should return 401 or 403 depending on middleware
        assert response.status_code in [401, 403]
