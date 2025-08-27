"""Token schemas."""

from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    """Token schema."""
    
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Token data schema."""
    
    username: Optional[str] = None
    user_id: Optional[int] = None
