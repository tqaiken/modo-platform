"""add subject assignment to users

Revision ID: 004_add_user_subject
Revises: 003_create_variants
Create Date: 2026-08-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_add_user_subject"
down_revision: Union[str, None] = "003_create_variants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "subject_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_users_subject_id",
        "users",
        "subjects",
        ["subject_id"],
        ["id"],
    )

    op.create_index(
        "ix_users_subject_id",
        "users",
        ["subject_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_subject_id",
        table_name="users",
    )

    op.drop_constraint(
        "fk_users_subject_id",
        "users",
        type_="foreignkey",
    )

    op.drop_column(
        "users",
        "subject_id",
    )