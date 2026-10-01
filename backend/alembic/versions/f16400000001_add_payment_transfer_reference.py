"""add payment transfer reference

Revision ID: f16400000001
Revises: f16300000001
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f16400000001"
down_revision: Union[str, None] = "f16300000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("transfer_reference", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "transfer_reference")