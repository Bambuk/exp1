"""add_customer_and_full_data_fields

Revision ID: 559cdae67d39
Revises: 4169cc34948d
Create Date: 2025-10-21 19:32:33.243803

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "559cdae67d39"
down_revision = "4169cc34948d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add customer field to tracker_tasks table
    op.add_column("tracker_tasks", sa.Column("customer", sa.Text(), nullable=True))

    # Add full_data JSONB field to tracker_tasks table
    op.add_column(
        "tracker_tasks",
        sa.Column("full_data", sa.dialects.postgresql.JSONB(), nullable=True),
    )

    # Add GIN index for fast JSONB queries on full_data
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracker_tasks_full_data_gin
        ON tracker_tasks USING gin(full_data jsonb_path_ops);
        """
    )


def downgrade() -> None:
    # Remove GIN index
    op.execute("DROP INDEX IF EXISTS idx_tracker_tasks_full_data_gin;")

    # Remove full_data column
    op.drop_column("tracker_tasks", "full_data")

    # Remove customer column
    op.drop_column("tracker_tasks", "customer")
