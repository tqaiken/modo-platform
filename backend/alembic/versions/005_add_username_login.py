"""add username authentication

Revision ID: 005_add_username_login
Revises: 004_add_user_subject
Create Date: 2026-08-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_add_username_login"
down_revision: Union[str, None] = "004_add_user_subject"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Сначала поле nullable, чтобы заполнить существующие строки.
    op.add_column(
        "users",
        sa.Column(
            "username",
            sa.String(length=100),
            nullable=True,
        ),
    )

    # Назначаем знакомые логины существующим тестовым аккаунтам.
    op.execute(
        """
        UPDATE users
        SET username = CASE
            WHEN lower(email) = 'admin@modo.kz'
                THEN 'admin'
            WHEN lower(email) = 'curator@modo.kz'
                THEN 'curator'
            WHEN lower(email) = 'verifier@modo.kz'
                THEN 'verifier'
            WHEN lower(email) = 'developer@modo.kz'
                THEN 'developer'
            ELSE 'user_' || id::text
        END
        WHERE username IS NULL
        """
    )

    # После заполнения логин становится обязательным.
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(length=100),
        nullable=False,
    )

    # Уникальный индекс одновременно ускоряет поиск при входе
    # и запрещает повторяющиеся логины.
    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
        unique=True,
    )

    # Email становится необязательным.
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    # Откат возможен только если у всех пользователей заполнен email.
    connection = op.get_bind()

    missing_email_count = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM users
            WHERE email IS NULL
            """
        )
    ).scalar_one()

    if missing_email_count > 0:
        raise RuntimeError(
            "Невозможно откатить миграцию: "
            "есть пользователи без email."
        )

    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    op.drop_index(
        "ix_users_username",
        table_name="users",
    )

    op.drop_column(
        "users",
        "username",
    )