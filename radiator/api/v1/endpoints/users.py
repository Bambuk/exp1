"""User endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.api.deps import get_current_active_user, get_current_active_superuser
from radiator.core.database import get_async_session
from radiator.crud.user import user
from radiator.schemas.user import User, UserCreate, UserUpdate

router = APIRouter()


@router.get("/me", response_model=User)
async def read_user_me(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current user information."""
    return current_user


@router.put("/me", response_model=User)
async def update_user_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """Update current user information."""
    return await user.update(db, db_obj=current_user, obj_in=user_in)


@router.get("/{user_id}", response_model=User)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """Get user by ID."""
    user_obj = await user.get(db, id=user_id)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user_obj


@router.get("/", response_model=List[User])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_async_session),
) -> List[User]:
    """Get all users (superuser only)."""
    return await user.get_multi(db, skip=skip, limit=limit)


@router.post("/", response_model=User)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """Create new user (superuser only)."""
    # Check if user already exists
    existing_user = await user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    existing_username = await user.get_by_username(db, username=user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    return await user.create(db, obj_in=user_in)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """Update user (superuser only)."""
    user_obj = await user.get(db, id=user_id)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return await user.update(db, db_obj=user_obj, obj_in=user_in)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Delete user (superuser only)."""
    user_obj = await user.get(db, id=user_id)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user_obj.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    
    await user.remove(db, id=user_id)
    return {"message": "User deleted successfully"}
