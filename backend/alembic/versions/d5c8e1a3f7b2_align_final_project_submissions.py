"""align final project submissions with TASK-5.4.3

Revision ID: d5c8e1a3f7b2
Revises: c4a7e9b2d1f6
Create Date: 2026-09-23 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5c8e1a3f7b2"
down_revision: str | None = "c4a7e9b2d1f6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "project_submissions",
        "user_id",
        new_column_name="student_id",
    )
    op.alter_column(
        "project_submissions",
        "repository_url",
        new_column_name="github_url",
    )
    op.alter_column(
        "project_submissions",
        "documentation_url",
        new_column_name="file_url",
    )

    op.drop_index(
        "ix_project_submissions_user_id",
        table_name="project_submissions",
    )
    op.create_index(
        "ix_project_submissions_student_id",
        "project_submissions",
        ["student_id"],
        unique=False,
    )

    op.add_column(
        "project_submissions",
        sa.Column("student_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "project_submissions",
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE project_submissions
            SET submitted_at = created_at
            WHERE status <> 'DRAFT'
              AND submitted_at IS NULL
            """
        )
    )

    duplicates = bind.execute(
        sa.text(
            """
            SELECT project_id, student_id, COUNT(*) AS submission_count
            FROM project_submissions
            GROUP BY project_id, student_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    if duplicates:
        raise RuntimeError(
            "Cannot enforce one active project submission per student/project; "
            "duplicate project_submissions rows already exist."
        )

    op.create_unique_constraint(
        "uq_project_submissions_project_student",
        "project_submissions",
        ["project_id", "student_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_project_submissions_project_student",
        "project_submissions",
        type_="unique",
    )

    op.drop_column(
        "project_submissions",
        "submitted_at",
    )
    op.drop_column(
        "project_submissions",
        "student_notes",
    )

    op.drop_index(
        "ix_project_submissions_student_id",
        table_name="project_submissions",
    )
    op.create_index(
        "ix_project_submissions_user_id",
        "project_submissions",
        ["user_id"],
        unique=False,
    )

    op.alter_column(
        "project_submissions",
        "file_url",
        new_column_name="documentation_url",
    )
    op.alter_column(
        "project_submissions",
        "github_url",
        new_column_name="repository_url",
    )
    op.alter_column(
        "project_submissions",
        "student_id",
        new_column_name="user_id",
    )
