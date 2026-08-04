"""add variant curator and publication fields

Revision ID: 008_add_variant_curator
Revises: 007_add_variant_review
Create Date: 2026-08-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "008_add_variant_curator"
down_revision: Union[str, None] = (
    "007_add_variant_review"
)
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """
    Добавляет данные публикации варианта
    куратором в банк заданий.

    curator_id:
        пользователь с ролью CURATOR,
        опубликовавший вариант.

    curator_comment:
        комментарий к включению варианта
        в банк заданий.

    published_at:
        дата и время перехода варианта
        из APPROVED в IN_BANK.
    """
    op.add_column(
        "variants",
        sa.Column(
            "curator_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "variants",
        sa.Column(
            "curator_comment",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "variants",
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_variants_curator_id",
        "variants",
        "users",
        ["curator_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_variants_curator_id",
        "variants",
        ["curator_id"],
        unique=False,
    )

    op.create_index(
        "ix_variants_published_at",
        "variants",
        ["published_at"],
        unique=False,
    )


def downgrade() -> None:
    """
    Удаляет данные публикации варианта.

    Статусы существующих вариантов
    при откате не изменяются.
    """
    op.drop_index(
        "ix_variants_published_at",
        table_name="variants",
    )

    op.drop_index(
        "ix_variants_curator_id",
        table_name="variants",
    )

    op.drop_constraint(
        "fk_variants_curator_id",
        "variants",
        type_="foreignkey",
    )

    op.drop_column(
        "variants",
        "published_at",
    )

    op.drop_column(
        "variants",
        "curator_comment",
    )

    op.drop_column(
        "variants",
        "curator_id",
    )