"""Fix items table removal migration

Revision ID: fix_items_migration
Revises: 5d4313ca2c02
Create Date: 2025-01-27 12:30:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_items_migration"
down_revision = "5d4313ca2c02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove items table and related functionality with safety checks."""
    # Check if table exists before trying to drop it
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "items" in inspector.get_table_names():
        # Drop indexes only if they exist
        indexes = inspector.get_indexes("items")
        index_names = [idx["name"] for idx in indexes]

        if "ix_items_id" in index_names:
            op.drop_index("ix_items_id", table_name="items")
        if "ix_items_title" in index_names:
            op.drop_index("ix_items_title", table_name="items")

        # Drop the table
        op.drop_table("items")


def downgrade() -> None:
    """Recreate items table and related functionality."""
    op.create_table(
        "items",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("title", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column("description", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("price", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column(
            "image_url", sa.VARCHAR(length=500), autoincrement=False, nullable=True
        ),
        sa.Column("is_available", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("owner_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="items_owner_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="items_pkey"),
    )
    op.create_index("ix_items_title", "items", ["title"], unique=False)
    op.create_index("ix_items_id", "items", ["id"], unique=False)
