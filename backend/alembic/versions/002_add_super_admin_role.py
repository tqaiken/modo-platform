"""add super admin role

Revision ID: 002_add_super_admin_role
Revises: 001_initial
Create Date: 2026-07-31
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "002_add_super_admin_role"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPER_ADMIN'")


def downgrade() -> None:
    # PostgreSQL does not safely support removing enum values in a simple migration.
    # Keep this as a no-op.
    pass