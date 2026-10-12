"""
add question versions

Revision ID: 010_add_question_versions
Revises: 009_add_variant_grade
Create Date: 2026-10-12
"""

from typing import (
    Sequence,
    Union,
)

from alembic import op
import sqlalchemy as sa


revision: str = (
    "010_add_question_versions"
)

down_revision: Union[
    str,
    None,
] = "009_add_variant_grade"

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
    Создаёт таблицу неизменяемых версий вопросов.
    """
    op.create_table(
        "question_versions",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "version_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "snapshot",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "change_reason",
            sa.String(
                length=255
            ),
            nullable=False,
        ),
        sa.Column(
            "change_details",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=(
                "fk_question_versions_"
                "question_id"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=(
                "fk_question_versions_"
                "created_by_id"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=(
                "pk_question_versions"
            ),
        ),
        sa.UniqueConstraint(
            "question_id",
            "version_number",
            name=(
                "uq_question_versions_"
                "question_version"
            ),
        ),
    )

    op.create_index(
        "ix_question_versions_id",
        "question_versions",
        ["id"],
        unique=False,
    )

    op.create_index(
        (
            "ix_question_versions_"
            "question_id"
        ),
        "question_versions",
        ["question_id"],
        unique=False,
    )

    op.create_index(
        (
            "ix_question_versions_"
            "created_by_id"
        ),
        "question_versions",
        ["created_by_id"],
        unique=False,
    )

    op.create_index(
        (
            "ix_question_versions_"
            "created_at"
        ),
        "question_versions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """
    Удаляет таблицу версий вопросов.
    """
    op.drop_index(
        (
            "ix_question_versions_"
            "created_at"
        ),
        table_name=(
            "question_versions"
        ),
    )

    op.drop_index(
        (
            "ix_question_versions_"
            "created_by_id"
        ),
        table_name=(
            "question_versions"
        ),
    )

    op.drop_index(
        (
            "ix_question_versions_"
            "question_id"
        ),
        table_name=(
            "question_versions"
        ),
    )

    op.drop_index(
        "ix_question_versions_id",
        table_name=(
            "question_versions"
        ),
    )

    op.drop_table(
        "question_versions"
    )