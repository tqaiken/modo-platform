"""add learning objectives and bilingual question fields

Revision ID: 006_add_learning_objectives
Revises: 005_add_username_login
Create Date: 2026-08-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "006_add_learning_objectives"
down_revision: Union[str, None] = "005_add_username_login"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    cognitive_level_enum = postgresql.ENUM(
        "BASIC",
        "MEDIUM",
        "HIGH",
        name="cognitivelevel",
        create_type=False,
    )

    cognitive_level_enum.create(
        bind,
        checkfirst=True,
    )

    op.create_table(
        "learning_objectives",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "subject_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "title_kz",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "title_ru",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name="fk_learning_objectives_subject_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "subject_id",
            "code",
            name="uq_learning_objectives_subject_code",
        ),
    )

    op.create_index(
        "ix_learning_objectives_id",
        "learning_objectives",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_learning_objectives_subject_id",
        "learning_objectives",
        ["subject_id"],
        unique=False,
    )

    op.create_index(
        "ix_learning_objectives_code",
        "learning_objectives",
        ["code"],
        unique=False,
    )

    op.create_index(
        "ix_learning_objectives_is_active",
        "learning_objectives",
        ["is_active"],
        unique=False,
    )

    op.add_column(
        "questions",
        sa.Column(
            "learning_objective_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "cognitive_level",
            cognitive_level_enum,
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "resource_kz",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "resource_ru",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "question_text_kz",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "question_text_ru",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "explanation_kz",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "questions",
        sa.Column(
            "explanation_ru",
            sa.Text(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_questions_learning_objective_id",
        "questions",
        "learning_objectives",
        ["learning_objective_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_questions_learning_objective_id",
        "questions",
        ["learning_objective_id"],
        unique=False,
    )

    op.create_index(
        "ix_questions_cognitive_level",
        "questions",
        ["cognitive_level"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_questions_cognitive_level",
        table_name="questions",
    )

    op.drop_index(
        "ix_questions_learning_objective_id",
        table_name="questions",
    )

    op.drop_constraint(
        "fk_questions_learning_objective_id",
        "questions",
        type_="foreignkey",
    )

    op.drop_column(
        "questions",
        "explanation_ru",
    )

    op.drop_column(
        "questions",
        "explanation_kz",
    )

    op.drop_column(
        "questions",
        "question_text_ru",
    )

    op.drop_column(
        "questions",
        "question_text_kz",
    )

    op.drop_column(
        "questions",
        "resource_ru",
    )

    op.drop_column(
        "questions",
        "resource_kz",
    )

    op.drop_column(
        "questions",
        "cognitive_level",
    )

    op.drop_column(
        "questions",
        "learning_objective_id",
    )

    op.drop_index(
        "ix_learning_objectives_is_active",
        table_name="learning_objectives",
    )

    op.drop_index(
        "ix_learning_objectives_code",
        table_name="learning_objectives",
    )

    op.drop_index(
        "ix_learning_objectives_subject_id",
        table_name="learning_objectives",
    )

    op.drop_index(
        "ix_learning_objectives_id",
        table_name="learning_objectives",
    )

    op.drop_table("learning_objectives")

    postgresql.ENUM(
        name="cognitivelevel",
    ).drop(
        op.get_bind(),
        checkfirst=True,
    )
