"""add quiz attempts and answers

Revision ID: f5a8c2d7e31b
Revises: e3b7c9d5f14a
Create Date: 2026-09-19 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f5a8c2d7e31b"
down_revision: str | None = "e3b7c9d5f14a"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'IN_PROGRESS'"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('IN_PROGRESS', 'COMPLETED')",
            name="ck_quiz_attempts_status",
        ),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_quiz_attempts_id"),
        "quiz_attempts",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_attempts_quiz_id"),
        "quiz_attempts",
        ["quiz_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_attempts_user_id"),
        "quiz_attempts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_attempts_status"),
        "quiz_attempts",
        ["status"],
        unique=False,
    )

    op.create_table(
        "quiz_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("selected_option_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_correct",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["quiz_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_option_id"],
            ["question_options.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_quiz_answers_attempt_question",
        ),
    )
    op.create_index(
        op.f("ix_quiz_answers_id"),
        "quiz_answers",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_answers_attempt_id"),
        "quiz_answers",
        ["attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_answers_question_id"),
        "quiz_answers",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_answers_selected_option_id"),
        "quiz_answers",
        ["selected_option_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_quiz_answers_selected_option_id"),
        table_name="quiz_answers",
    )
    op.drop_index(
        op.f("ix_quiz_answers_question_id"),
        table_name="quiz_answers",
    )
    op.drop_index(
        op.f("ix_quiz_answers_attempt_id"),
        table_name="quiz_answers",
    )
    op.drop_index(op.f("ix_quiz_answers_id"), table_name="quiz_answers")
    op.drop_table("quiz_answers")

    op.drop_index(op.f("ix_quiz_attempts_status"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_user_id"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_quiz_id"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_id"), table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
