"""Base for Alembic migrations without async engine creation."""

from radiator.core.database import Base
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory

__all__ = ["Base"]
