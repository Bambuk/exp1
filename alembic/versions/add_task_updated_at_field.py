"""Add task_updated_at field to tracker_tasks table

Revision ID: add_task_updated_at_field
Revises: 5d4313ca2c02
Create Date: 2025-01-27 12:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_task_updated_at_field"
down_revision = "5d4313ca2c02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add task_updated_at field to tracker_tasks table."""
    op.add_column(
        "tracker_tasks", sa.Column("task_updated_at", sa.DateTime(), nullable=True)
    )

    # Create index for better performance on queries by task_updated_at
    op.create_index(
        "idx_tracker_tasks_task_updated", "tracker_tasks", ["task_updated_at"]
    )


def downgrade() -> None:
    """Remove task_updated_at field from tracker_tasks table."""
    op.drop_index("idx_tracker_tasks_task_updated", "tracker_tasks")
    op.drop_column("tracker_tasks", "task_updated_at")
