"""API dependencies."""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.core.database import get_async_session
from radiator.core.security import decode_token
from radiator.crud.user import user
from radiator.schemas.user import User

# Security scheme
security = HTTPBearer()


async def get_current_user(
    db: AsyncSession = Depends(get_async_session),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    payload = decode_token(token)
    username: str = payload.get("sub")
    
    if username is None:
        raise credentials_exception
    
    current_user = await user.get_by_username(db, username=username)
    if current_user is None:
        raise credentials_exception
    
    return current_user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user doesn't have enough privileges",
        )
    return current_user
