"""align final project models with TASK-5.4.1

Revision ID: b3f6c1a9d2e7
Revises: 854ed1c1bdd8
Create Date: 2026-09-23 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3f6c1a9d2e7"
down_revision: str | None = "854ed1c1bdd8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "training_projects",
        sa.Column(
            "passing_score",
            sa.Integer(),
            server_default=sa.text("75"),
            nullable=False,
        ),
    )
    op.drop_column("training_projects", "evaluation_rubric")

    op.drop_column("project_requirements", "title")
    op.alter_column(
        "project_requirements",
        "ordering",
        new_column_name="order",
    )


def downgrade() -> None:
    op.add_column(
        "project_requirements",
        sa.Column(
            "title",
            sa.String(length=255),
            server_default=sa.text(""),
            nullable=False,
        ),
    )
    op.alter_column(
        "project_requirements",
        "order",
        new_column_name="ordering",
    )
    op.alter_column(
        "project_requirements",
        "title",
        server_default=None,
    )

    op.add_column(
        "training_projects",
        sa.Column("evaluation_rubric", sa.JSON(), nullable=True),
    )
    op.drop_column("training_projects", "passing_score")
