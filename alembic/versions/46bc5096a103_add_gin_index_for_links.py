"""add_gin_index_for_links

Revision ID: 46bc5096a103
Revises: ef79ab4625d7
Create Date: 2025-10-10 21:53:57.629172

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "46bc5096a103"
down_revision = "ef79ab4625d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, convert links column from JSON to JSONB for better performance
    op.execute(
        """
        ALTER TABLE tracker_tasks
        ALTER COLUMN links TYPE jsonb USING links::jsonb;
    """
    )

    # Add GIN index for JSONB links column for fast JSONB queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracker_tasks_links_gin
        ON tracker_tasks USING gin(links jsonb_path_ops);
    """
    )


def downgrade() -> None:
    # Remove GIN index
    op.execute("DROP INDEX IF EXISTS idx_tracker_tasks_links_gin;")

    # Convert links column back to JSON
    op.execute(
        """
        ALTER TABLE tracker_tasks
        ALTER COLUMN links TYPE json USING links::json;
    """
    )
