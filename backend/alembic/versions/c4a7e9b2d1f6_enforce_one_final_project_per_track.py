"""enforce one final project per track

Revision ID: c4a7e9b2d1f6
Revises: b3f6c1a9d2e7
Create Date: 2026-09-23 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "c4a7e9b2d1f6"
down_revision: str | None = "b3f6c1a9d2e7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_training_projects_track_id",
        "training_projects",
        ["track_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_training_projects_track_id",
        "training_projects",
        type_="unique",
    )
