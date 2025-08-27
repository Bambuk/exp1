"""Item schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ItemBase(BaseModel):
    """Base item schema."""
    
    title: str
    description: Optional[str] = None
    price: Optional[int] = None  # Price in cents
    image_url: Optional[str] = None
    is_available: bool = True


class ItemCreate(ItemBase):
    """Schema for creating an item."""
    
    pass


class ItemUpdate(BaseModel):
    """Schema for updating an item."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class ItemInDBBase(ItemBase):
    """Base item schema with database fields."""
    
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        
        from_attributes = True


class Item(ItemInDBBase):
    """Item schema for API responses."""
    
    pass


class ItemInDB(ItemInDBBase):
    """Item schema with database fields."""
    
    pass
