"""add graduation rules and certificates

Revision ID: f2a5c7d9e1b3
Revises: e8b1c4d7a2f6
Create Date: 2026-09-24 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a5c7d9e1b3"
down_revision = "e8b1c4d7a2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graduation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ordering", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "track_id",
            "code",
            name="uq_graduation_rules_track_code",
        ),
    )
    op.create_index(
        "ix_graduation_rules_track_id",
        "graduation_rules",
        ["track_id"],
    )
    op.create_index(
        "ix_graduation_rules_ordering",
        "graduation_rules",
        ["ordering"],
    )

    op.create_table(
        "graduation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evaluated_at", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "student_id",
            "track_id",
            name="uq_graduation_results_student_track",
        ),
    )
    op.create_index(
        "ix_graduation_results_student_id",
        "graduation_results",
        ["student_id"],
    )
    op.create_index(
        "ix_graduation_results_track_id",
        "graduation_results",
        ["track_id"],
    )
    op.create_index(
        "ix_graduation_results_status",
        "graduation_results",
        ["status"],
    )

    op.create_table(
        "graduation_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["graduation_results.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["graduation_rules.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "result_id",
            "rule_id",
            name="uq_graduation_checks_result_rule",
        ),
    )
    op.create_index(
        "ix_graduation_checks_result_id",
        "graduation_checks",
        ["result_id"],
    )
    op.create_index(
        "ix_graduation_checks_rule_id",
        "graduation_checks",
        ["rule_id"],
    )

    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("graduation_result_id", sa.Integer(), nullable=False),
        sa.Column("certificate_number", sa.String(length=128), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ISSUED"),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["graduation_result_id"],
            ["graduation_results.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "graduation_result_id",
            name="uq_certificates_graduation_result",
        ),
        sa.UniqueConstraint(
            "certificate_number",
            name="uq_certificates_certificate_number",
        ),
    )
    op.create_index(
        "ix_certificates_student_id",
        "certificates",
        ["student_id"],
    )
    op.create_index(
        "ix_certificates_track_id",
        "certificates",
        ["track_id"],
    )
    op.create_index(
        "ix_certificates_graduation_result_id",
        "certificates",
        ["graduation_result_id"],
    )
    op.create_index(
        "ix_certificates_certificate_number",
        "certificates",
        ["certificate_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_certificates_certificate_number",
        table_name="certificates",
    )
    op.drop_index(
        "ix_certificates_graduation_result_id",
        table_name="certificates",
    )
    op.drop_index(
        "ix_certificates_track_id",
        table_name="certificates",
    )
    op.drop_index(
        "ix_certificates_student_id",
        table_name="certificates",
    )
    op.drop_table("certificates")

    op.drop_index(
        "ix_graduation_checks_rule_id",
        table_name="graduation_checks",
    )
    op.drop_index(
        "ix_graduation_checks_result_id",
        table_name="graduation_checks",
    )
    op.drop_table("graduation_checks")

    op.drop_index(
        "ix_graduation_results_status",
        table_name="graduation_results",
    )
    op.drop_index(
        "ix_graduation_results_track_id",
        table_name="graduation_results",
    )
    op.drop_index(
        "ix_graduation_results_student_id",
        table_name="graduation_results",
    )
    op.drop_table("graduation_results")

    op.drop_index(
        "ix_graduation_rules_ordering",
        table_name="graduation_rules",
    )
    op.drop_index(
        "ix_graduation_rules_track_id",
        table_name="graduation_rules",
    )
    op.drop_table("graduation_rules")