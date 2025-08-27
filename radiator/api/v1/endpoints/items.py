"""Item endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.api.deps import get_current_active_user
from radiator.core.database import get_async_session
from radiator.crud.item import item
from radiator.models.user import User
from radiator.schemas.item import Item, ItemCreate, ItemUpdate

router = APIRouter()


@router.get("/", response_model=List[Item])
async def read_items(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session),
) -> List[Item]:
    """Get all available items."""
    return await item.get_available(db, skip=skip, limit=limit)


@router.get("/search", response_model=List[Item])
async def search_items(
    title: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session),
) -> List[Item]:
    """Search items by title."""
    return await item.search_by_title(db, title=title, skip=skip, limit=limit)


@router.get("/my", response_model=List[Item])
async def read_my_items(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[Item]:
    """Get current user's items."""
    return await item.get_by_owner(
        db, owner_id=current_user.id, skip=skip, limit=limit
    )


@router.get("/{item_id}", response_model=Item)
async def read_item(
    item_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> Item:
    """Get item by ID."""
    item_obj = await item.get(db, id=item_id)
    if not item_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return item_obj


@router.post("/", response_model=Item)
async def create_item(
    item_in: ItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Item:
    """Create new item."""
    item_data = item_in.dict()
    item_data["owner_id"] = current_user.id
    return await item.create(db, obj_in=ItemCreate(**item_data))


@router.put("/{item_id}", response_model=Item)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Item:
    """Update item."""
    item_obj = await item.get(db, id=item_id)
    if not item_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    
    if item_obj.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return await item.update(db, db_obj=item_obj, obj_in=item_in)


@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Delete item."""
    item_obj = await item.get(db, id=item_id)
    if not item_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    
    if item_obj.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    await item.remove(db, id=item_id)
    return {"message": "Item deleted successfully"}
