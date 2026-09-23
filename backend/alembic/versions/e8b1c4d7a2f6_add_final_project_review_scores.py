"""add score to final project reviews

Revision ID: e8b1c4d7a2f6
Revises: d5c8e1a3f7b2
Create Date: 2026-09-23 16:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8b1c4d7a2f6"
down_revision: str | None = "d5c8e1a3f7b2"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_reviews",
        sa.Column("score", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(
        "project_reviews",
        "score",
    )
