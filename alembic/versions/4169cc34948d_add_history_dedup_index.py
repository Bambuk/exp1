"""add_history_dedup_index

Revision ID: 4169cc34948d
Revises: fbc2721a43d3
Create Date: 2025-10-18 17:46:15.768418

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4169cc34948d"
down_revision = "fbc2721a43d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create composite index for efficient duplicate detection
    # This index optimizes the PARTITION BY operation in window functions
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracker_history_dedup
        ON tracker_task_history (task_id, status, start_date);
    """
    )


def downgrade() -> None:
    # Remove the composite index
    op.execute("DROP INDEX IF EXISTS idx_tracker_history_dedup;")
