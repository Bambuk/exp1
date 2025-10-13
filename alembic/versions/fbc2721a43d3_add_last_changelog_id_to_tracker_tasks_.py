"""Add last_changelog_id to tracker_tasks for incremental history sync

Revision ID: fbc2721a43d3
Revises: 46bc5096a103
Create Date: 2025-10-13 18:49:49.943103

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fbc2721a43d3"
down_revision = "46bc5096a103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add last_changelog_id field to tracker_tasks table."""
    # Add the column
    op.add_column(
        "tracker_tasks", sa.Column("last_changelog_id", sa.String(255), nullable=True)
    )

    # Create index for better performance on queries by last_changelog_id
    op.create_index(
        "idx_tracker_tasks_last_changelog_id", "tracker_tasks", ["last_changelog_id"]
    )


def downgrade() -> None:
    """Remove last_changelog_id field from tracker_tasks table."""
    # Drop the index first
    op.drop_index("idx_tracker_tasks_last_changelog_id", "tracker_tasks")

    # Drop the column
    op.drop_column("tracker_tasks", "last_changelog_id")
