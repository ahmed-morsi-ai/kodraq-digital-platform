"""add AI request logs

Revision ID: d7f1a9c4e26b
Revises: c6e9a4b2d17f
Create Date: 2026-09-19 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7f1a9c4e26b"
down_revision: str | None = "c6e9a4b2d17f"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_request_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("request_type", sa.String(length=64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_request_logs_id"),
        "ai_request_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_request_logs_user_id"),
        "ai_request_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_request_logs_provider"),
        "ai_request_logs",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_request_logs_model"),
        "ai_request_logs",
        ["model"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_request_logs_request_type"),
        "ai_request_logs",
        ["request_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_request_logs_success"),
        "ai_request_logs",
        ["success"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_request_logs_success"), table_name="ai_request_logs")
    op.drop_index(
        op.f("ix_ai_request_logs_request_type"),
        table_name="ai_request_logs",
    )
    op.drop_index(op.f("ix_ai_request_logs_model"), table_name="ai_request_logs")
    op.drop_index(
        op.f("ix_ai_request_logs_provider"),
        table_name="ai_request_logs",
    )
    op.drop_index(op.f("ix_ai_request_logs_user_id"), table_name="ai_request_logs")
    op.drop_index(op.f("ix_ai_request_logs_id"), table_name="ai_request_logs")
    op.drop_table("ai_request_logs")
