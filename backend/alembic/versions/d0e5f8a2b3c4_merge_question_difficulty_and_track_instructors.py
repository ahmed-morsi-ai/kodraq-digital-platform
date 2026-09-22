"""merge question difficulty and track instructors heads

Revision ID: d0e5f8a2b3c4
Revises: c4e7a9b2d5f1, c9d4e7f1a2b3
Create Date: 2026-09-22 00:00:00.000000

"""
from collections.abc import Sequence

revision: str = "d0e5f8a2b3c4"
down_revision: tuple[str, str] = ("c4e7a9b2d5f1", "c9d4e7f1a2b3")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
