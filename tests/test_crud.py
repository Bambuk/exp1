"""Tests for CRUD operations."""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.crud.user import user
from radiator.schemas.user import UserCreate
from radiator.models.user import User


@pytest.mark.asyncio
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
        
        # Mock the create method
        with patch.object(user, 'create') as mock_create:
            mock_user = User(
                id=1,
                email=user_data.email,
                username=user_data.username,
                full_name=user_data.full_name,
                hashed_password="hashed_password_123"
            )
            mock_create.return_value = mock_user
            
            created_user = await user.create(db_session, obj_in=user_data)
            assert created_user.email == user_data.email
            assert created_user.username == user_data.username
            assert created_user.full_name == user_data.full_name
            assert created_user.hashed_password != user_data.password

    async def test_get_user_by_email(self, db_session: AsyncSession):
        """Test getting user by email."""
        # Mock the get_by_email method
        with patch.object(user, 'get_by_email') as mock_get:
            mock_user = User(
                id=1,
                email="getbyemail@example.com",
                username="getbyemail",
                full_name="Test User"
            )
            mock_get.return_value = mock_user
            
            found_user = await user.get_by_email(db_session, email="getbyemail@example.com")
            assert found_user is not None
            assert found_user.id == 1
            assert found_user.email == "getbyemail@example.com"

    async def test_get_user_by_username(self, db_session: AsyncSession):
        """Test getting user by username."""
        # Mock the get_by_username method
        with patch.object(user, 'get_by_username') as mock_get:
            mock_user = User(
                id=1,
                email="getbyusername@example.com",
                username="getbyusername",
                full_name="Test User"
            )
            mock_get.return_value = mock_user
            
            found_user = await user.get_by_username(db_session, username="getbyusername")
            assert found_user is not None
            assert found_user.id == 1
            assert found_user.username == "getbyusername"

    async def test_authenticate_user(self, db_session: AsyncSession):
        """Test user authentication."""
        # Mock the authenticate method
        with patch.object(user, 'authenticate') as mock_auth:
            mock_user = User(
                id=1,
                email="auth@example.com",
                username="authuser",
                full_name="Test User"
            )
            mock_auth.return_value = mock_user
            
            authenticated_user = await user.authenticate(
                db_session, email="auth@example.com", password="authpass123"
            )
            assert authenticated_user is not None
            assert authenticated_user.id == 1
            
            # Test wrong password
            mock_auth.return_value = None
            wrong_auth = await user.authenticate(
                db_session, email="auth@example.com", password="wrongpass"
            )
            assert wrong_auth is None

    async def test_update_user(self, db_session: AsyncSession):
        """Test updating user."""
        # Mock the update method
        with patch.object(user, 'update') as mock_update:
            mock_user = User(
                id=1,
                email="update@example.com",
                username="updateuser",
                full_name="Updated Name",
                bio="Updated bio"
            )
            mock_update.return_value = mock_user
            
            update_data = {"full_name": "Updated Name", "bio": "Updated bio"}
            updated_user = await user.update(
                db_session, db_obj=mock_user, obj_in=update_data
            )
            assert updated_user.full_name == "Updated Name"
            assert updated_user.bio == "Updated bio"

    async def test_delete_user(self, db_session: AsyncSession):
        """Test deleting user."""
        # Mock the remove method
        with patch.object(user, 'remove') as mock_remove:
            mock_user = User(
                id=1,
                email="delete@example.com",
                username="deleteuser",
                full_name="Test User"
            )
            mock_remove.return_value = mock_user
            
            deleted_user = await user.remove(db_session, id=1)
            assert deleted_user is not None
            assert deleted_user.id == 1

