"""create variants and connect questions

Revision ID: 003_create_variants
Revises: 002_add_super_admin_role
Create Date: 2026-07-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "003_create_variants"
down_revision: Union[str, None] = "002_add_super_admin_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    variant_status_enum = postgresql.ENUM(
        "DRAFT",
        "VERIFICATION",
        "REVISION",
        "APPROVED",
        "IN_BANK",
        name="variantstatus",
        create_type=False,
    )

    variant_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "variants",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "title",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "subject_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "developer_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            variant_status_enum,
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name="fk_variants_subject_id",
        ),
        sa.ForeignKeyConstraint(
            ["developer_id"],
            ["users.id"],
            name="fk_variants_developer_id",
        ),
    )

    op.create_index(
        "ix_variants_id",
        "variants",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_variants_status",
        "variants",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_variants_developer_id",
        "variants",
        ["developer_id"],
        unique=False,
    )

    op.add_column(
        "questions",
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "order_number",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )

    op.create_foreign_key(
        "fk_questions_variant_id",
        "questions",
        "variants",
        ["variant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_questions_variant_id",
        "questions",
        ["variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_questions_variant_id",
        table_name="questions",
    )

    op.drop_constraint(
        "fk_questions_variant_id",
        "questions",
        type_="foreignkey",
    )

    op.drop_column(
        "questions",
        "order_number",
    )

    op.drop_column(
        "questions",
        "variant_id",
    )

    op.drop_index(
        "ix_variants_developer_id",
        table_name="variants",
    )

    op.drop_index(
        "ix_variants_status",
        table_name="variants",
    )

    op.drop_index(
        "ix_variants_id",
        table_name="variants",
    )

    op.drop_table("variants")

    postgresql.ENUM(
        name="variantstatus",
    ).drop(
        op.get_bind(),
        checkfirst=True,
    )