"""align submission domain models

Revision ID: d4a8511554d8
Revises: 8e2435463795
Create Date: 2026-09-25 20:54:53.236606

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4a8511554d8"
down_revision: str | None = "8e2435463795"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

STATES = (
    "'DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'CHANGES_REQUIRED', 'APPROVED', 'REJECTED'"
)


def upgrade() -> None:
    op.add_column("submissions", sa.Column("grade", sa.Integer(), nullable=True))
    op.add_column(
        "submissions",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("submission_files", "file_path", new_column_name="file_url")
    op.alter_column("submission_files", "content_type", new_column_name="file_type")
    op.alter_column(
        "submission_files",
        "file_size",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column("submission_reviews", "feedback", new_column_name="feedback_text")
    op.drop_constraint(
        "ck_submission_reviews_resulting_status",
        "submission_reviews",
        type_="check",
    )
    op.drop_index(
        "ix_submission_reviews_resulting_status", table_name="submission_reviews"
    )
    op.alter_column(
        "submission_reviews",
        "resulting_status",
        new_column_name="status_transition",
    )
    op.create_check_constraint(
        "ck_submission_reviews_status_transition",
        "submission_reviews",
        f"status_transition IN ({STATES})",
    )
    op.create_index(
        "ix_submission_reviews_status_transition",
        "submission_reviews",
        ["status_transition"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_submission_reviews_status_transition", table_name="submission_reviews"
    )
    op.drop_constraint(
        "ck_submission_reviews_status_transition",
        "submission_reviews",
        type_="check",
    )
    op.alter_column(
        "submission_reviews",
        "status_transition",
        new_column_name="resulting_status",
    )
    op.create_check_constraint(
        "ck_submission_reviews_resulting_status",
        "submission_reviews",
        f"resulting_status IN ({STATES})",
    )
    op.create_index(
        "ix_submission_reviews_resulting_status",
        "submission_reviews",
        ["resulting_status"],
    )
    op.alter_column("submission_reviews", "feedback_text", new_column_name="feedback")
    # The old schema requires a size even when newer records have none recorded.
    op.execute("UPDATE submission_files SET file_size = 0 WHERE file_size IS NULL")
    op.alter_column(
        "submission_files",
        "file_size",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column("submission_files", "file_type", new_column_name="content_type")
    op.alter_column("submission_files", "file_url", new_column_name="file_path")
    op.drop_column("submissions", "submitted_at")
    op.drop_column("submissions", "grade")
