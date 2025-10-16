"""add links field to tracker_tasks

Revision ID: ef79ab4625d7
Revises: 6f01179c965e
Create Date: 2025-10-10 17:03:12.848235

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ef79ab4625d7"
down_revision = "6f01179c965e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add links column to tracker_tasks table
    op.add_column("tracker_tasks", sa.Column("links", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove links column from tracker_tasks table
    op.drop_column("tracker_tasks", "links")
