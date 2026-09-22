"""add track instructor mapping

Revision ID: c4e7a9b2d5f1
Revises: b7c4e1a9d2f6
Create Date: 2026-09-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4e7a9b2d5f1"
down_revision: str | None = "b7c4e1a9d2f6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "track_instructors",
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["instructor_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("track_id", "instructor_id"),
        sa.UniqueConstraint(
            "track_id",
            "instructor_id",
            name="uq_track_instructors_track_instructor",
        ),
    )
    op.create_index(
        op.f("ix_track_instructors_instructor_id"),
        "track_instructors",
        ["instructor_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_track_instructors_instructor_id"),
        table_name="track_instructors",
    )
    op.drop_table("track_instructors")
