"""Add quiz/question module context and foundation constraints.

Revision ID: f15300000001
Revises: e7b252600001
"""

import sqlalchemy as sa
from alembic import op

revision = "f15300000001"
down_revision = "e7b252600001"
branch_labels = None
depends_on = None

CONSTRAINTS = {
    "questions": {
        "ck_questions_difficulty": "difficulty >= 1",
        "ck_questions_points": "points > 0",
        "ck_questions_text": "length(trim(text)) > 0",
        "ck_questions_type": "length(trim(question_type)) > 0",
    },
    "question_options": {"ck_question_options_text": "length(trim(text)) > 0"},
    "quizzes": {
        "ck_quizzes_passing_score": "passing_score BETWEEN 0 AND 100",
        "ck_quizzes_time_limit": "time_limit_minutes IS NULL OR time_limit_minutes > 0",
        "ck_quizzes_title": "length(trim(title)) > 0",
    },
    "quiz_questions": {"ck_quiz_questions_ordering": "ordering >= 0"},
}


def upgrade() -> None:
    for table in ("questions", "quizzes"):
        op.add_column(table, sa.Column("module_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_module_id",
            table,
            "track_modules",
            ["module_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(f"ix_{table}_module_id", table, ["module_id"])
    for table, constraints in CONSTRAINTS.items():
        for name, condition in constraints.items():
            op.create_check_constraint(name, table, condition)
    op.alter_column("questions", "points", server_default="1")
    op.alter_column("question_options", "is_correct", server_default=sa.false())
    op.alter_column("quizzes", "is_active", server_default=sa.true())
    op.alter_column("quiz_questions", "ordering", server_default="0")


def downgrade() -> None:
    for table, column in (
        ("questions", "points"),
        ("question_options", "is_correct"),
        ("quizzes", "is_active"),
        ("quiz_questions", "ordering"),
    ):
        op.alter_column(table, column, server_default=None)
    for table, constraints in CONSTRAINTS.items():
        for name in constraints:
            op.drop_constraint(name, table, type_="check")
    for table in ("questions", "quizzes"):
        op.drop_index(f"ix_{table}_module_id", table_name=table)
        op.drop_constraint(f"fk_{table}_module_id", table, type_="foreignkey")
        op.drop_column(table, "module_id")
