"""Add tracker tables

Revision ID: add_tracker_tables
Revises: 99e284f2522b
Create Date: 2024-01-01 12:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_tracker_tables"
down_revision = "99e284f2522b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tracker_tasks table
    op.create_table(
        "tracker_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracker_id", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("assignee", sa.String(length=255), nullable=True),
        sa.Column("business_client", sa.Text(), nullable=True),
        sa.Column("team", sa.String(length=255), nullable=True),
        sa.Column("prodteam", sa.String(length=255), nullable=True),
        sa.Column("profit_forecast", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for tracker_tasks
    op.create_index(
        "idx_tracker_tasks_tracker_id", "tracker_tasks", ["tracker_id"], unique=True
    )
    op.create_index("idx_tracker_tasks_last_sync", "tracker_tasks", ["last_sync_at"])

    # Create tracker_task_history table
    op.create_table(
        "tracker_task_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("tracker_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=255), nullable=False),
        sa.Column("status_display", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for tracker_task_history
    op.create_index(
        "idx_tracker_history_task_status", "tracker_task_history", ["task_id", "status"]
    )
    op.create_index(
        "idx_tracker_history_dates", "tracker_task_history", ["start_date", "end_date"]
    )

    # Create tracker_sync_logs table
    op.create_table(
        "tracker_sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sync_started_at", sa.DateTime(), nullable=False),
        sa.Column("sync_completed_at", sa.DateTime(), nullable=True),
        sa.Column("tasks_processed", sa.Integer(), nullable=True),
        sa.Column("tasks_created", sa.Integer(), nullable=True),
        sa.Column("tasks_updated", sa.Integer(), nullable=True),
        sa.Column("errors_count", sa.Integer(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for tracker_sync_logs
    op.create_index("idx_tracker_sync_logs_status", "tracker_sync_logs", ["status"])
    op.create_index(
        "idx_tracker_sync_logs_started", "tracker_sync_logs", ["sync_started_at"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_tracker_sync_logs_started", table_name="tracker_sync_logs")
    op.drop_index("idx_tracker_sync_logs_status", table_name="tracker_sync_logs")
    op.drop_index("idx_tracker_history_dates", table_name="tracker_task_history")
    op.drop_index("idx_tracker_history_task_status", table_name="tracker_task_history")
    op.drop_index("idx_tracker_tasks_last_sync", table_name="tracker_tasks")
    op.drop_index("idx_tracker_tasks_tracker_id", table_name="tracker_tasks")

    # Drop tables
    op.drop_table("tracker_sync_logs")
    op.drop_table("tracker_task_history")
    op.drop_table("tracker_tasks")
