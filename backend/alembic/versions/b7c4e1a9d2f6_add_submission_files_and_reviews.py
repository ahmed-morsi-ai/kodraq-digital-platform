"""add submission files and reviews

Revision ID: b7c4e1a9d2f6
Revises: a9c7e5f1d2b4
Create Date: 2026-09-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c4e1a9d2f6"
down_revision: str | None = "a9c7e5f1d2b4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "submission_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_submission_files_submission_id"),
        "submission_files",
        ["submission_id"],
        unique=False,
    )

    op.create_table(
        "submission_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("resulting_status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "resulting_status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', "
            "'CHANGES_REQUIRED', 'APPROVED', 'REJECTED')",
            name="ck_submission_reviews_resulting_status",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_submission_reviews_submission_id"),
        "submission_reviews",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_submission_reviews_reviewer_id"),
        "submission_reviews",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_submission_reviews_resulting_status"),
        "submission_reviews",
        ["resulting_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_submission_reviews_resulting_status"),
        table_name="submission_reviews",
    )
    op.drop_index(
        op.f("ix_submission_reviews_reviewer_id"),
        table_name="submission_reviews",
    )
    op.drop_index(
        op.f("ix_submission_reviews_submission_id"),
        table_name="submission_reviews",
    )
    op.drop_table("submission_reviews")
    op.drop_index(
        op.f("ix_submission_files_submission_id"),
        table_name="submission_files",
    )
    op.drop_table("submission_files")
