"""add graduation evaluations and gate checks

Revision ID: c6e9a4b2d17f
Revises: b8d2f6a4c19e
Create Date: 2026-09-19 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c6e9a4b2d17f"
down_revision: str | None = "b8d2f6a4c19e"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graduation_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column(
            "is_eligible",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('PENDING', 'GRADUATED', 'FAILED_GATES')",
            name="ck_graduation_evaluations_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_graduation_evaluations_id"),
        "graduation_evaluations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graduation_evaluations_user_id"),
        "graduation_evaluations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graduation_evaluations_track_id"),
        "graduation_evaluations",
        ["track_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graduation_evaluations_status"),
        "graduation_evaluations",
        ["status"],
        unique=False,
    )

    op.create_table(
        "graduation_gate_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("gate_key", sa.String(length=64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("required_value", sa.Float(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["graduation_evaluations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_id",
            "gate_key",
            name="uq_graduation_gate_checks_evaluation_gate",
        ),
    )
    op.create_index(
        op.f("ix_graduation_gate_checks_id"),
        "graduation_gate_checks",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graduation_gate_checks_evaluation_id"),
        "graduation_gate_checks",
        ["evaluation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graduation_gate_checks_gate_key"),
        "graduation_gate_checks",
        ["gate_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_graduation_gate_checks_gate_key"),
        table_name="graduation_gate_checks",
    )
    op.drop_index(
        op.f("ix_graduation_gate_checks_evaluation_id"),
        table_name="graduation_gate_checks",
    )
    op.drop_index(
        op.f("ix_graduation_gate_checks_id"),
        table_name="graduation_gate_checks",
    )
    op.drop_table("graduation_gate_checks")

    op.drop_index(
        op.f("ix_graduation_evaluations_status"),
        table_name="graduation_evaluations",
    )
    op.drop_index(
        op.f("ix_graduation_evaluations_track_id"),
        table_name="graduation_evaluations",
    )
    op.drop_index(
        op.f("ix_graduation_evaluations_user_id"),
        table_name="graduation_evaluations",
    )
    op.drop_index(
        op.f("ix_graduation_evaluations_id"),
        table_name="graduation_evaluations",
    )
    op.drop_table("graduation_evaluations")
