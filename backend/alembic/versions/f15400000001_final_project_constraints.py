"""Validate final-project requirements, grading bounds and review decisions.

Revision ID: f15400000001
Revises: f15300000002
"""

from alembic import op
import sqlalchemy as sa

revision = "f15400000001"
down_revision = "f15300000002"
branch_labels = None
depends_on = None

CHECKS = (
    ("training_projects", "ck_training_projects_title", "length(trim(title)) > 0"),
    (
        "training_projects",
        "ck_training_projects_passing_score",
        "passing_score BETWEEN 0 AND 100",
    ),
    (
        "project_requirements",
        "ck_project_requirements_description",
        "length(trim(description)) > 0",
    ),
    ("project_requirements", "ck_project_requirements_order", '"order" >= 0'),
    (
        "project_reviews",
        "ck_project_reviews_score",
        "score IS NULL OR score BETWEEN 0 AND 100",
    ),
    (
        "project_reviews",
        "ck_project_reviews_decision",
        "status_decision IN ('UNDER_REVIEW', 'CHANGES_REQUIRED', 'APPROVED', 'REJECTED')",
    ),
)
DEFAULTS = (
    ("training_projects", "is_active", sa.Boolean(), "true"),
    ("project_requirements", "is_mandatory", sa.Boolean(), "true"),
    ("project_requirements", "order", sa.Integer(), "0"),
)


def upgrade():
    bind = op.get_bind()
    # Reject invalid historical data explicitly rather than deleting or changing
    # requirements and grades during deployment. Alembic rolls back the migration.
    for table, name, condition in CHECKS:
        invalid = bind.scalar(
            sa.text(f"SELECT count(*) FROM {table} WHERE NOT ({condition})")
        )
        if invalid:
            raise RuntimeError(
                f"Final-project migration blocked: {invalid} rows violate {name}. Correct these records before upgrading."
            )
    if bind.scalar(
        sa.text("SELECT count(*) FROM project_requirements WHERE description IS NULL")
    ):
        raise RuntimeError(
            "Final-project migration blocked: requirements need non-null descriptions."
        )
    for table, name, condition in CHECKS:
        op.create_check_constraint(name, table, condition)
    op.alter_column(
        "project_requirements", "description", existing_type=sa.Text(), nullable=False
    )
    for table, column, datatype, default in DEFAULTS:
        op.alter_column(
            table, column, existing_type=datatype, server_default=sa.text(default)
        )


def downgrade():
    for table, column, datatype, _ in reversed(DEFAULTS):
        op.alter_column(table, column, existing_type=datatype, server_default=None)
    op.alter_column(
        "project_requirements", "description", existing_type=sa.Text(), nullable=True
    )
    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(name, table, type_="check")
