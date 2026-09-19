"""add project submissions and reviews

Revision ID: b8d2f6a4c19e
Revises: a7c4e9f2b16d
Create Date: 2026-09-19 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8d2f6a4c19e"
down_revision: str | None = "a7c4e9f2b16d"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("repository_url", sa.String(length=512), nullable=True),
        sa.Column("live_url", sa.String(length=512), nullable=True),
        sa.Column("documentation_url", sa.String(length=512), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
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
            "status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', "
            "'CHANGES_REQUIRED', 'APPROVED', 'REJECTED')",
            name="ck_project_submissions_status",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["training_projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_submissions_id"),
        "project_submissions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_submissions_project_id"),
        "project_submissions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_submissions_user_id"),
        "project_submissions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_submissions_status"),
        "project_submissions",
        ["status"],
        unique=False,
    )

    op.create_table(
        "project_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("rubric_scores", sa.JSON(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status_decision", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["project_submissions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_reviews_id"),
        "project_reviews",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_reviews_submission_id"),
        "project_reviews",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_reviews_reviewer_id"),
        "project_reviews",
        ["reviewer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_project_reviews_reviewer_id"),
        table_name="project_reviews",
    )
    op.drop_index(
        op.f("ix_project_reviews_submission_id"),
        table_name="project_reviews",
    )
    op.drop_index(op.f("ix_project_reviews_id"), table_name="project_reviews")
    op.drop_table("project_reviews")

    op.drop_index(
        op.f("ix_project_submissions_status"),
        table_name="project_submissions",
    )
    op.drop_index(
        op.f("ix_project_submissions_user_id"),
        table_name="project_submissions",
    )
    op.drop_index(
        op.f("ix_project_submissions_project_id"),
        table_name="project_submissions",
    )
    op.drop_index(op.f("ix_project_submissions_id"), table_name="project_submissions")
    op.drop_table("project_submissions")
