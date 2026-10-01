"""Add descriptions to lessons.

Revision ID: f16200000001
Revises: f16100000001
"""

from alembic import op
import sqlalchemy as sa

revision = "f16200000001"
down_revision = "f16100000001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lessons", sa.Column("description", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("lessons", "description")