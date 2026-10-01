"""Preserve submit/resubmit timestamps for submission history.

Revision ID: e7b252600001
Revises: d4a8511554d8
"""

from alembic import op
import sqlalchemy as sa

revision = "e7b252600001"
down_revision = "d4a8511554d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_submission_attempts_submission_id", "submission_attempts", ["submission_id"]
    )
    # Only the latest historical timestamp is recoverable from the old schema.
    op.execute(
        "INSERT INTO submission_attempts (submission_id, submitted_at) SELECT id, submitted_at FROM submissions WHERE submitted_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_table("submission_attempts")
