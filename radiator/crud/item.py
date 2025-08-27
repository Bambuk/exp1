"""CRUD operations for items."""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from radiator.crud.base import CRUDBase
from radiator.models.item import Item
from radiator.schemas.item import ItemCreate, ItemUpdate


class CRUDItem(CRUDBase[Item, ItemCreate, ItemUpdate]):
    """CRUD operations for items."""

    async def get_by_owner(
        self, db: AsyncSession, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Item]:
        """Get items by owner ID."""
        result = await db.execute(
            select(Item)
            .where(Item.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_available(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Item]:
        """Get available items."""
        result = await db.execute(
            select(Item)
            .where(Item.is_available == True)  # noqa: E712
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def search_by_title(
        self, db: AsyncSession, *, title: str, skip: int = 0, limit: int = 100
    ) -> List[Item]:
        """Search items by title."""
        result = await db.execute(
            select(Item)
            .where(Item.title.ilike(f"%{title}%"))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


item = CRUDItem(Item)
