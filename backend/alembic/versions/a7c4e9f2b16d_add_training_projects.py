"""add training projects and requirements

Revision ID: a7c4e9f2b16d
Revises: f5a8c2d7e31b
Create Date: 2026-09-19 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7c4e9f2b16d"
down_revision: str | None = "f5a8c2d7e31b"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("evaluation_rubric", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_projects_id"),
        "training_projects",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_projects_track_id"),
        "training_projects",
        ["track_id"],
        unique=False,
    )

    op.create_table(
        "project_requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["training_projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_requirements_id"),
        "project_requirements",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_requirements_project_id"),
        "project_requirements",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_project_requirements_project_id"),
        table_name="project_requirements",
    )
    op.drop_index(
        op.f("ix_project_requirements_id"),
        table_name="project_requirements",
    )
    op.drop_table("project_requirements")

    op.drop_index(
        op.f("ix_training_projects_track_id"),
        table_name="training_projects",
    )
    op.drop_index(
        op.f("ix_training_projects_id"),
        table_name="training_projects",
    )
    op.drop_table("training_projects")
