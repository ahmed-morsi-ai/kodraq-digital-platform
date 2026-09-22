"""add track assignment config

Revision ID: a9c7e5f1d2b4
Revises: e4b8c1d6f29a
Create Date: 2026-09-20 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9c7e5f1d2b4"
down_revision: str | None = "e4b8c1d6f29a"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "track_assignment_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("passing_score_threshold", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("is_strict_progression", sa.Boolean(), nullable=False),
        sa.Column("late_submission_policy", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "passing_score_threshold BETWEEN 0 AND 100",
            name="ck_track_assignment_config_passing_score",
        ),
        sa.CheckConstraint(
            "max_retries >= 0",
            name="ck_track_assignment_config_max_retries",
        ),
        sa.CheckConstraint(
            "late_submission_policy IN ('ACCEPTED', 'REJECTED', 'PENALIZED')",
            name="ck_track_assignment_config_late_policy",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("track_id", name="uq_track_assignment_config_track_id"),
    )
    op.create_index(
        op.f("ix_track_assignment_configs_id"),
        "track_assignment_configs",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_track_assignment_configs_id"),
        table_name="track_assignment_configs",
    )
    op.drop_table("track_assignment_configs")
