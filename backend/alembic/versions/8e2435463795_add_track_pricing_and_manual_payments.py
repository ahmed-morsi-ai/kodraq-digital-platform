"""add track pricing and manual payments

Revision ID: 8e2435463795
Revises: f2a5c7d9e1b3
Create Date: 2026-09-24 02:07:33.736138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e2435463795"
down_revision: Union[str, None] = "f2a5c7d9e1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payment_method", sa.String(length=32), nullable=False),
        sa.Column("receipt_url", sa.String(length=1024), nullable=False),
        sa.Column("rejection_reason", sa.String(length=512), nullable=True),
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
            "status IN "
            "('PENDING_VERIFICATION', 'VERIFIED', 'REJECTED')",
            name="ck_payments_status",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_payments_id"),
        "payments",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payments_track_id"),
        "payments",
        ["track_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payments_user_id"),
        "payments",
        ["user_id"],
        unique=False,
    )

    op.add_column(
        "tracks",
        sa.Column(
            "price",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0.0"),
            nullable=False,
        ),
    )
    op.add_column(
        "tracks",
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'EGP'"),
            nullable=False,
        ),
    )
    op.add_column(
        "tracks",
        sa.Column(
            "is_premium",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.alter_column(
        "tracks",
        "price",
        server_default=None,
    )
    op.alter_column(
        "tracks",
        "currency",
        server_default=None,
    )
    op.alter_column(
        "tracks",
        "is_premium",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("tracks", "is_premium")
    op.drop_column("tracks", "currency")
    op.drop_column("tracks", "price")

    op.drop_index(
        op.f("ix_payments_user_id"),
        table_name="payments",
    )
    op.drop_index(
        op.f("ix_payments_track_id"),
        table_name="payments",
    )
    op.drop_index(
        op.f("ix_payments_id"),
        table_name="payments",
    )
    op.drop_table("payments")
