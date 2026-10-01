"""Persist quiz attempt deadlines, passing thresholds and finalized results.

Revision ID: f15300000002
Revises: f15300000001
"""

import sqlalchemy as sa
from alembic import op

revision = "f15300000002"
down_revision = "f15300000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quiz_attempts",
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "quiz_attempts", sa.Column("passing_score", sa.Integer(), nullable=True)
    )
    op.add_column(
        "quiz_attempts", sa.Column("result_snapshot", sa.JSON(), nullable=True)
    )
    op.execute(
        "UPDATE quiz_attempts AS a SET passing_score = q.passing_score, deadline_at = a.started_at + q.time_limit_minutes * INTERVAL '1 minute' FROM quizzes AS q WHERE a.quiz_id = q.id"
    )


def downgrade() -> None:
    for column in ("result_snapshot", "passing_score", "deadline_at"):
        op.drop_column("quiz_attempts", column)
