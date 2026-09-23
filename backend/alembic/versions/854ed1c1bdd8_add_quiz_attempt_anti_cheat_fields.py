"""add quiz attempt anti cheat fields

Revision ID: 854ed1c1bdd8
Revises: d0e5f8a2b3c4
Create Date: 2026-09-23 00:47:00.382552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "854ed1c1bdd8"
down_revision: Union[str, None] = "d0e5f8a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quiz_attempts",
        sa.Column(
            "is_flagged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "quiz_attempts",
        sa.Column(
            "flag_reason",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_quiz_attempts_is_flagged",
        "quiz_attempts",
        ["is_flagged"],
        unique=False,
    )
    op.alter_column(
        "quiz_attempts",
        "is_flagged",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quiz_attempts_is_flagged",
        table_name="quiz_attempts",
    )
    op.drop_column("quiz_attempts", "flag_reason")
    op.drop_column("quiz_attempts", "is_flagged")
