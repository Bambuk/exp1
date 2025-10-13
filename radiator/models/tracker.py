"""Tracker models for Yandex Tracker integration."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from radiator.core.database import Base


class TrackerTask(Base):
    """Model for storing tracker tasks."""

    __tablename__ = "tracker_tasks"

    id = Column(Integer, primary_key=True, index=True)
    tracker_id = Column(String(255), unique=True, nullable=False, index=True)
    key = Column(String(255), nullable=True, index=True)  # Task code like TEST-123
    summary = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    assignee = Column(String(255), nullable=True)
    business_client = Column(Text, nullable=True)
    team = Column(String(255), nullable=True)
    prodteam = Column(String(255), nullable=True)
    profit_forecast = Column(String(255), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, default=datetime.utcnow)
    task_updated_at = Column(
        DateTime, nullable=True
    )  # When task was last updated in tracker

    # Links to other tasks (JSONB array)
    links = Column(JSONB, nullable=True)  # Array of link objects from API

    # Incremental sync support
    last_changelog_id = Column(
        String(255), nullable=True
    )  # ID of last processed changelog entry

    def __repr__(self) -> str:
        return f"<TrackerTask(id={self.id}, tracker_id='{self.tracker_id}')>"


class TrackerTaskHistory(Base):
    """Model for storing task status history."""

    __tablename__ = "tracker_task_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Integer, nullable=False, index=True)
    tracker_id = Column(String(255), nullable=False, index=True)
    status = Column(String(255), nullable=False)
    status_display = Column(String(255), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TrackerTaskHistory(id={self.id}, task_id={self.task_id}, status='{self.status}')>"


class TrackerSyncLog(Base):
    """Model for tracking sync operations."""

    __tablename__ = "tracker_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_started_at = Column(DateTime, nullable=False)
    sync_completed_at = Column(DateTime, nullable=True)
    tasks_processed = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    tasks_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(Text, nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed

    def __repr__(self) -> str:
        return f"<TrackerSyncLog(id={self.id}, status='{self.status}')>"


# Create indexes for better performance
Index("idx_tracker_tasks_tracker_id", TrackerTask.tracker_id)
Index("idx_tracker_tasks_key", TrackerTask.key)  # Index for task codes
Index("idx_tracker_tasks_last_sync", TrackerTask.last_sync_at)
Index(
    "idx_tracker_tasks_task_updated", TrackerTask.task_updated_at
)  # Index for tracker updates
Index(
    "idx_tracker_tasks_last_changelog_id", TrackerTask.last_changelog_id
)  # Index for incremental sync
Index(
    "idx_tracker_history_task_status",
    TrackerTaskHistory.task_id,
    TrackerTaskHistory.status,
)
Index(
    "idx_tracker_history_dates",
    TrackerTaskHistory.start_date,
    TrackerTaskHistory.end_date,
)
Index("idx_tracker_sync_logs_status", TrackerSyncLog.status)
Index("idx_tracker_sync_logs_started", TrackerSyncLog.sync_started_at)
