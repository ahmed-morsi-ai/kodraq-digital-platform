"""Add quiz data to lessons.

Revision ID: f16300000001
Revises: f16200000001
"""

from alembic import op
import sqlalchemy as sa

revision = "f16300000001"
down_revision = "f16200000001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lessons", sa.Column("quiz_data", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("lessons", "quiz_data")