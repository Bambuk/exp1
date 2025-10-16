"""merge heads

Revision ID: 6f01179c965e
Revises: add_task_updated_at_field, d0701f4164ab
Create Date: 2025-09-29 20:24:10.784761

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "6f01179c965e"
down_revision = ("add_task_updated_at_field", "d0701f4164ab")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
