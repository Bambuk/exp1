"""Tests for item endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.unit
class TestItems:
    """Test item endpoints."""

    def test_get_items(self, client: TestClient):
        """Test getting all available items."""
        response = client.get("/api/v1/items/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_items(self, client: TestClient):
        """Test searching items by title."""
        response = client.get("/api/v1/items/search?title=test")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_item(self, client: TestClient):
        """Test creating a new item."""
        # First register and login to get token
        user_data = {
            "email": "itemcreator@example.com",
            "username": "itemcreator",
            "password": "itempass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Create item
        item_data = {
            "title": "Test Item",
            "description": "Test Description",
            "price": 1000,
            "is_available": True
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/v1/items/", json=item_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == item_data["title"]
        assert data["description"] == item_data["description"]
        assert data["price"] == item_data["price"]

    def test_create_item_unauthorized(self, client: TestClient):
        """Test creating item without authentication."""
        item_data = {
            "title": "Unauthorized Item",
            "description": "This should fail",
            "price": 500
        }
        response = client.post("/api/v1/items/", json=item_data)
        assert response.status_code == 401

    def test_get_item_by_id(self, client: TestClient):
        """Test getting item by ID."""
        # First create an item
        user_data = {
            "email": "itemgetter@example.com",
            "username": "itemgetter",
            "password": "itempass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        item_data = {
            "title": "Get Item",
            "description": "Item to get",
            "price": 750
        }
        headers = {"Authorization": f"Bearer {token}"}
        create_response = client.post("/api/v1/items/", json=item_data, headers=headers)
        item_id = create_response.json()["id"]
        
        # Get item by ID
        response = client.get(f"/api/v1/items/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == item_data["title"]

    def test_get_item_not_found(self, client: TestClient):
        """Test getting non-existent item."""
        response = client.get("/api/v1/items/999")
        assert response.status_code == 404
        assert "Item not found" in response.json()["detail"]

    def test_update_item(self, client: TestClient):
        """Test updating an item."""
        # First create an item
        user_data = {
            "email": "itemupdater@example.com",
            "username": "itemupdater",
            "password": "itempass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        item_data = {
            "title": "Update Item",
            "description": "Item to update",
            "price": 600
        }
        headers = {"Authorization": f"Bearer {token}"}
        create_response = client.post("/api/v1/items/", json=item_data, headers=headers)
        item_id = create_response.json()["id"]
        
        # Update item
        update_data = {
            "title": "Updated Item",
            "price": 800
        }
        response = client.put(f"/api/v1/items/{item_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["price"] == update_data["price"]

    def test_update_item_unauthorized(self, client: TestClient):
        """Test updating item without authentication."""
        update_data = {
            "title": "Unauthorized Update"
        }
        response = client.put("/api/v1/items/1", json=update_data)
        assert response.status_code == 401

    def test_delete_item(self, client: TestClient):
        """Test deleting an item."""
        # First create an item
        user_data = {
            "email": "itemdeleter@example.com",
            "username": "itemdeleter",
            "password": "itempass123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        item_data = {
            "title": "Delete Item",
            "description": "Item to delete",
            "price": 400
        }
        headers = {"Authorization": f"Bearer {token}"}
        create_response = client.post("/api/v1/items/", json=item_data, headers=headers)
        item_id = create_response.json()["id"]
        
        # Delete item
        response = client.delete(f"/api/v1/items/{item_id}", headers=headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_item_unauthorized(self, client: TestClient):
        """Test deleting item without authentication."""
        response = client.delete("/api/v1/items/1")
        assert response.status_code == 401
