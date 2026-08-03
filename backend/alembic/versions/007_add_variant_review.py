"""add variant reviewer and review comment

Revision ID: 007_add_variant_review
Revises: 006_add_learning_objectives
Create Date: 2026-08-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007_add_variant_review"
down_revision: Union[str, None] = (
    "006_add_learning_objectives"
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
    Добавляет результат проверки всего варианта.

    reviewer_id:
        пользователь с ролью VERIFIER,
        который принял итоговое решение.

    review_comment:
        итоговая рецензия при утверждении
        или возврате варианта на доработку.
    """
    op.add_column(
        "variants",
        sa.Column(
            "reviewer_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "variants",
        sa.Column(
            "review_comment",
            sa.Text(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_variants_reviewer_id",
        "variants",
        "users",
        ["reviewer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_variants_reviewer_id",
        "variants",
        ["reviewer_id"],
        unique=False,
    )


def downgrade() -> None:
    """
    Удаляет данные итоговой проверки варианта.

    Статусы и даты вариантов при откате
    не изменяются.
    """
    op.drop_index(
        "ix_variants_reviewer_id",
        table_name="variants",
    )

    op.drop_constraint(
        "fk_variants_reviewer_id",
        "variants",
        type_="foreignkey",
    )

    op.drop_column(
        "variants",
        "review_comment",
    )

    op.drop_column(
        "variants",
        "reviewer_id",
    )