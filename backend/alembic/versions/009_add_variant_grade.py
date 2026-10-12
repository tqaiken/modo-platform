"""add grade to variants

Revision ID: 009_add_variant_grade
Revises: 008_add_variant_curator
Create Date: 2026-09-11
"""

from typing import (
    Sequence,
    Union,
)

from alembic import op
import sqlalchemy as sa


revision: str = "009_add_variant_grade"

down_revision: Union[
    str,
    None,
] = "008_add_variant_curator"

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
    Добавляет класс обучения к варианту.

    Поле временно допускает NULL для совместимости
    с вариантами, созданными до этой миграции.

    Новые варианты обязаны передавать класс
    через схему VariantCreate.
    """
    op.add_column(
        "variants",
        sa.Column(
            "grade",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_variants_grade_range",
        "variants",
        (
            "grade IS NULL "
            "OR grade BETWEEN 1 AND 12"
        ),
    )

    op.create_index(
        "ix_variants_grade",
        "variants",
        ["grade"],
        unique=False,
    )


def downgrade() -> None:
    """
    Удаляет класс обучения из вариантов.
    """
    op.drop_index(
        "ix_variants_grade",
        table_name="variants",
    )

    op.drop_constraint(
        "ck_variants_grade_range",
        "variants",
        type_="check",
    )

    op.drop_column(
        "variants",
        "grade",
    )