"""Tests for CRUD operations."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.crud.user import user
from radiator.crud.item import item
from radiator.schemas.user import UserCreate
from radiator.schemas.item import ItemCreate
from radiator.models.user import User
from radiator.models.item import Item


@pytest.mark.unit
class TestUserCRUD:
    """Test user CRUD operations."""

    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a user."""
        user_data = UserCreate(
            email="crud@example.com",
            username="cruduser",
            full_name="CRUD User",
            password="crudpass123"
        )
        
        created_user = await user.create(db_session, obj_in=user_data)
        assert created_user.email == user_data.email
        assert created_user.username == user_data.username
        assert created_user.full_name == user_data.full_name
        assert created_user.hashed_password != user_data.password

    async def test_get_user_by_email(self, db_session: AsyncSession):
        """Test getting user by email."""
        # Create user first
        user_data = UserCreate(
            email="getbyemail@example.com",
            username="getbyemail",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Get user by email
        found_user = await user.get_by_email(db_session, email=user_data.email)
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == user_data.email

    async def test_get_user_by_username(self, db_session: AsyncSession):
        """Test getting user by username."""
        # Create user first
        user_data = UserCreate(
            email="getbyusername@example.com",
            username="getbyusername",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Get user by username
        found_user = await user.get_by_username(db_session, username=user_data.username)
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == user_data.username

    async def test_authenticate_user(self, db_session: AsyncSession):
        """Test user authentication."""
        # Create user first
        user_data = UserCreate(
            email="auth@example.com",
            username="authuser",
            password="authpass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Authenticate with correct credentials
        authenticated_user = await user.authenticate(
            db_session, email=user_data.email, password=user_data.password
        )
        assert authenticated_user is not None
        assert authenticated_user.id == created_user.id
        
        # Authenticate with wrong password
        wrong_auth = await user.authenticate(
            db_session, email=user_data.email, password="wrongpass"
        )
        assert wrong_auth is None

    async def test_update_user(self, db_session: AsyncSession):
        """Test updating user."""
        # Create user first
        user_data = UserCreate(
            email="update@example.com",
            username="updateuser",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Update user
        update_data = {"full_name": "Updated Name", "bio": "Updated bio"}
        updated_user = await user.update(
            db_session, db_obj=created_user, obj_in=update_data
        )
        
        assert updated_user.full_name == update_data["full_name"]
        assert updated_user.bio == update_data["bio"]

    async def test_delete_user(self, db_session: AsyncSession):
        """Test deleting user."""
        # Create user first
        user_data = UserCreate(
            email="delete@example.com",
            username="deleteuser",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Delete user
        deleted_user = await user.remove(db_session, id=created_user.id)
        assert deleted_user.id == created_user.id
        
        # Verify user is deleted
        found_user = await user.get(db_session, id=created_user.id)
        assert found_user is None


@pytest.mark.unit
class TestItemCRUD:
    """Test item CRUD operations."""

    async def test_create_item(self, db_session: AsyncSession):
        """Test creating an item."""
        # Create user first
        user_data = UserCreate(
            email="itemuser@example.com",
            username="itemuser",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Create item
        item_data = ItemCreate(
            title="Test Item",
            description="Test Description",
            price=1000,
            is_available=True
        )
        
        # Note: We need to manually set owner_id since it's not in ItemCreate schema
        item_dict = item_data.dict()
        item_dict["owner_id"] = created_user.id
        
        created_item = await item.create(db_session, obj_in=ItemCreate(**item_dict))
        assert created_item.title == item_data.title
        assert created_item.description == item_data.description
        assert created_item.price == item_data.price
        assert created_item.owner_id == created_user.id

    async def test_get_items_by_owner(self, db_session: AsyncSession):
        """Test getting items by owner."""
        # Create user first
        user_data = UserCreate(
            email="owner@example.com",
            username="owner",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Create items
        item1_data = ItemCreate(title="Item 1", price=100)
        item2_data = ItemCreate(title="Item 2", price=200)
        
        item1_dict = item1_data.dict()
        item1_dict["owner_id"] = created_user.id
        item2_dict = item2_data.dict()
        item2_dict["owner_id"] = created_user.id
        
        await item.create(db_session, obj_in=ItemCreate(**item1_dict))
        await item.create(db_session, obj_in=ItemCreate(**item2_dict))
        
        # Get items by owner
        owner_items = await item.get_by_owner(db_session, owner_id=created_user.id)
        assert len(owner_items) == 2
        assert all(item.owner_id == created_user.id for item in owner_items)

    async def test_get_available_items(self, db_session: AsyncSession):
        """Test getting available items."""
        # Create user first
        user_data = UserCreate(
            email="available@example.com",
            username="available",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Create available and unavailable items
        available_item = ItemCreate(title="Available", is_available=True)
        unavailable_item = ItemCreate(title="Unavailable", is_available=False)
        
        available_dict = available_item.dict()
        available_dict["owner_id"] = created_user.id
        unavailable_dict = unavailable_item.dict()
        unavailable_dict["owner_id"] = created_user.id
        
        await item.create(db_session, obj_in=ItemCreate(**available_dict))
        await item.create(db_session, obj_in=ItemCreate(**unavailable_dict))
        
        # Get available items
        available_items = await item.get_available(db_session)
        assert len(available_items) == 1
        assert available_items[0].title == "Available"
        assert available_items[0].is_available is True

    async def test_search_items_by_title(self, db_session: AsyncSession):
        """Test searching items by title."""
        # Create user first
        user_data = UserCreate(
            email="search@example.com",
            username="search",
            password="pass123"
        )
        created_user = await user.create(db_session, obj_in=user_data)
        
        # Create items with different titles
        item1_data = ItemCreate(title="Apple iPhone", price=1000)
        item2_data = ItemCreate(title="Samsung Galaxy", price=800)
        item3_data = ItemCreate(title="Google Pixel", price=600)
        
        for item_data in [item1_data, item2_data, item3_data]:
            item_dict = item_data.dict()
            item_dict["owner_id"] = created_user.id
            await item.create(db_session, obj_in=ItemCreate(**item_dict))
        
        # Search for items containing "phone"
        phone_items = await item.search_by_title(db_session, title="phone")
        assert len(phone_items) == 1
        assert "iPhone" in phone_items[0].title
        
        # Search for items containing "Google"
        google_items = await item.search_by_title(db_session, title="Google")
        assert len(google_items) == 1
        assert "Google" in google_items[0].title
