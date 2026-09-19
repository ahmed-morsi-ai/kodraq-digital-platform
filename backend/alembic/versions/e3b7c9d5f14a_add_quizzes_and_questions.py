"""add quizzes and questions

Revision ID: e3b7c9d5f14a
Revises: d1e6f8a3b42c
Create Date: 2026-09-19 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3b7c9d5f14a"
down_revision: str | None = "d1e6f8a3b42c"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_questions_id"), "questions", ["id"], unique=False)
    op.create_index(
        op.f("ix_questions_track_id"), "questions", ["track_id"], unique=False
    )
    op.create_index(
        op.f("ix_questions_lesson_id"), "questions", ["lesson_id"], unique=False
    )

    op.create_table(
        "question_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_question_options_id"),
        "question_options",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_options_question_id"),
        "question_options",
        ["question_id"],
        unique=False,
    )

    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("passing_score", sa.Integer(), nullable=False),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quizzes_id"), "quizzes", ["id"], unique=False)
    op.create_index(
        op.f("ix_quizzes_track_id"), "quizzes", ["track_id"], unique=False
    )
    op.create_index(
        op.f("ix_quizzes_lesson_id"), "quizzes", ["lesson_id"], unique=False
    )

    op.create_table(
        "quiz_questions",
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("quiz_id", "question_id"),
        sa.UniqueConstraint(
            "quiz_id",
            "question_id",
            name="uq_quiz_questions_quiz_question",
        ),
    )
    op.create_index(
        op.f("ix_quiz_questions_quiz_id"),
        "quiz_questions",
        ["quiz_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_questions_question_id"),
        "quiz_questions",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_questions_ordering"),
        "quiz_questions",
        ["ordering"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_quiz_questions_ordering"), table_name="quiz_questions")
    op.drop_index(
        op.f("ix_quiz_questions_question_id"),
        table_name="quiz_questions",
    )
    op.drop_index(
        op.f("ix_quiz_questions_quiz_id"),
        table_name="quiz_questions",
    )
    op.drop_table("quiz_questions")

    op.drop_index(op.f("ix_quizzes_lesson_id"), table_name="quizzes")
    op.drop_index(op.f("ix_quizzes_track_id"), table_name="quizzes")
    op.drop_index(op.f("ix_quizzes_id"), table_name="quizzes")
    op.drop_table("quizzes")

    op.drop_index(
        op.f("ix_question_options_question_id"),
        table_name="question_options",
    )
    op.drop_index(op.f("ix_question_options_id"), table_name="question_options")
    op.drop_table("question_options")

    op.drop_index(op.f("ix_questions_lesson_id"), table_name="questions")
    op.drop_index(op.f("ix_questions_track_id"), table_name="questions")
    op.drop_index(op.f("ix_questions_id"), table_name="questions")
    op.drop_table("questions")
