"""Tests for CRUD operations."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.crud.user import user
from radiator.schemas.user import UserCreate
from radiator.models.user import User


@pytest.mark.unit
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

