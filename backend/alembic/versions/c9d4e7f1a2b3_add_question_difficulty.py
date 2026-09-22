"""add question difficulty

Revision ID: c9d4e7f1a2b3
Revises: f5a8c2d7e31b
Create Date: 2026-09-22 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9d4e7f1a2b3"
down_revision: str | None = "f5a8c2d7e31b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column(
            "difficulty",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("questions", "difficulty")
