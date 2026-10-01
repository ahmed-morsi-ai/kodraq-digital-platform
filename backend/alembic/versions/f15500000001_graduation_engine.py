"""Align graduation snapshots and retire duplicate evaluation tables without deleting history.

Revision ID: f15500000001
Revises: f15400000001
"""

from alembic import op
import sqlalchemy as sa

revision = "f15500000001"
down_revision = "f15400000001"
branch_labels = None
depends_on = None

CONSTRAINTS = {
    "graduation_rules": {
        "ck_graduation_rules_threshold": "threshold IS NULL OR threshold BETWEEN 0 AND 100",
        "ck_graduation_rules_ordering": "ordering >= 0",
    },
    "graduation_results": {
        "ck_graduation_results_status": "status IN ('PENDING', 'GRADUATED', 'NOT_GRADUATED')",
        "ck_graduation_results_score": "overall_score IS NULL OR overall_score BETWEEN 0 AND 100",
        "ck_graduation_results_eligible": "status != 'GRADUATED' OR eligible",
    },
    "graduation_checks": {
        "ck_graduation_checks_score": "score IS NULL OR score BETWEEN 0 AND 100",
        "ck_graduation_checks_required": "required_value IS NULL OR required_value BETWEEN 0 AND 100",
    },
}


def upgrade():
    # Archive tables retain their rows and internal relationship, not live user/track FKs.
    # A rollback restores the original names and foreign keys.
    for column in ("user_id", "track_id"):
        op.drop_constraint(
            f"graduation_evaluations_{column}_fkey",
            "graduation_evaluations",
            type_="foreignkey",
        )
    op.rename_table("graduation_evaluations", "graduation_evaluations_archive")
    op.rename_table("graduation_gate_checks", "graduation_gate_checks_archive")
    for table, column in (
        ("graduation_results", "overall_score"),
        ("graduation_checks", "score"),
        ("certificates", "final_score"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.Integer(),
            type_=sa.Float(),
            postgresql_using=f"{column}::double precision",
        )
    op.alter_column(
        "graduation_results",
        "evaluated_at",
        existing_type=sa.String(64),
        type_=sa.DateTime(timezone=True),
        postgresql_using="evaluated_at::timestamptz",
    )
    op.add_column(
        "graduation_results",
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "graduation_results", sa.Column("finalized_by", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_graduation_results_finalizer",
        "graduation_results",
        "users",
        ["finalized_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "graduation_checks", sa.Column("gate_key", sa.String(64), nullable=True)
    )
    op.add_column(
        "graduation_checks", sa.Column("required_value", sa.Float(), nullable=True)
    )
    op.add_column(
        "graduation_checks", sa.Column("failure_reason", sa.Text(), nullable=True)
    )
    op.execute(
        "UPDATE graduation_checks AS c SET gate_key=r.code, required_value=r.threshold FROM graduation_rules AS r WHERE c.rule_id=r.id"
    )
    op.alter_column("graduation_checks", "gate_key", nullable=False)
    op.alter_column(
        "graduation_checks",
        "details",
        existing_type=sa.Text(),
        type_=sa.JSON(),
        postgresql_using="CASE WHEN details IS NULL THEN NULL ELSE json_build_object('legacy_text', details) END",
    )
    for table in (
        "graduation_rules",
        "graduation_results",
        "graduation_checks",
        "certificates",
    ):
        for column in ("created_at", "updated_at"):
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(),
                type_=sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            )
    op.alter_column("graduation_results", "status", server_default="PENDING")
    op.execute(
        "UPDATE graduation_results SET finalized_at=COALESCE(evaluated_at, created_at) WHERE status='GRADUATED'"
    )
    for table, checks in CONSTRAINTS.items():
        for name, expression in checks.items():
            op.create_check_constraint(name, table, expression)


def downgrade():
    # The old schema cannot represent fractional grades. Refuse rather than truncate them.
    connection = op.get_bind()
    for table, column in (
        ("graduation_results", "overall_score"),
        ("graduation_checks", "score"),
        ("certificates", "final_score"),
    ):
        if connection.scalar(
            sa.text(
                f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {column} != trunc({column}::numeric))"
            )
        ):
            raise RuntimeError(
                "Cannot downgrade graduation while fractional scores exist; preserve/export these records first."
            )
    for table, checks in CONSTRAINTS.items():
        for name in checks:
            op.drop_constraint(name, table, type_="check")
    op.alter_column("graduation_results", "status", server_default=None)
    for table in (
        "graduation_rules",
        "graduation_results",
        "graduation_checks",
        "certificates",
    ):
        for column in ("created_at", "updated_at"):
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.DateTime(),
                server_default=None,
                postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            )
    op.alter_column(
        "graduation_checks",
        "details",
        existing_type=sa.JSON(),
        type_=sa.Text(),
        postgresql_using="CASE WHEN details IS NULL THEN NULL WHEN details::jsonb ? 'legacy_text' THEN details->>'legacy_text' ELSE details::text END",
    )
    for column in ("failure_reason", "required_value", "gate_key"):
        op.drop_column("graduation_checks", column)
    op.drop_constraint(
        "fk_graduation_results_finalizer", "graduation_results", type_="foreignkey"
    )
    op.drop_column("graduation_results", "finalized_by")
    op.drop_column("graduation_results", "finalized_at")
    op.alter_column(
        "graduation_results",
        "evaluated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.String(64),
        postgresql_using="evaluated_at::text",
    )
    for table, column in (
        ("graduation_results", "overall_score"),
        ("graduation_checks", "score"),
        ("certificates", "final_score"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.Float(),
            type_=sa.Integer(),
            postgresql_using=f"{column}::integer",
        )
    op.rename_table("graduation_gate_checks_archive", "graduation_gate_checks")
    op.rename_table("graduation_evaluations_archive", "graduation_evaluations")
    for column, target in (("user_id", "users"), ("track_id", "tracks")):
        op.create_foreign_key(
            f"graduation_evaluations_{column}_fkey",
            "graduation_evaluations",
            target,
            [column],
            ["id"],
            ondelete="CASCADE",
        )
