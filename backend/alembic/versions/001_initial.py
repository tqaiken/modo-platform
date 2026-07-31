"""initial schema — all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-07-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM types
    user_role_enum = postgresql.ENUM(
        "DEVELOPER",
        "VERIFIER",
        "CURATOR",
        name="userrole",
        create_type=False,
    )

    question_status_enum = postgresql.ENUM(
        "DRAFT",
        "VERIFICATION",
        "REVISION",
        "IN_BANK",
        name="questionstatus",
        create_type=False,
    )

    language_enum = postgresql.ENUM(
        "RU",
        "KZ",
        name="language",
        create_type=False,
    )

    log_action_enum = postgresql.ENUM(
        "CREATED",
        "UPDATED",
        "SUBMITTED",
        "APPROVED",
        "REJECTED",
        "RETURNED",
        "EDITED_BY_VERIFIER",
        "STATUS_CHANGED",
        "MEDIA_UPLOADED",
        "MEDIA_DELETED",
        name="logaction",
        create_type=False,
    )

    user_role_enum.create(op.get_bind(), checkfirst=True)
    question_status_enum.create(op.get_bind(), checkfirst=True)
    language_enum.create(op.get_bind(), checkfirst=True)
    log_action_enum.create(op.get_bind(), checkfirst=True)

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="DEVELOPER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # subjects
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("title_kz", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_subjects_code", "subjects", ["code"])

    # questions
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("language", language_enum, nullable=False, server_default="RU"),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("topic", sa.String(255), nullable=True),
        sa.Column("difficulty", sa.Integer(), server_default=sa.text("1")),
        sa.Column("status", question_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_questions_status", "questions", ["status"])

    # media_files
    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("r2_key", sa.String(1000), unique=True, nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("public_url", sa.String(2000), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # review_comments
    op.create_table(
        "review_comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # question_logs
    op.create_table(
        "question_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", log_action_enum, nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_question_logs_question_id", "question_logs", ["question_id"])
    op.create_index("ix_question_logs_timestamp", "question_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_question_logs_timestamp", table_name="question_logs")
    op.drop_index("ix_question_logs_question_id", table_name="question_logs")
    op.drop_table("question_logs")
    op.drop_table("review_comments")
    op.drop_table("media_files")
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_subjects_code", table_name="subjects")
    op.drop_table("subjects")
    op.drop_table("users")

    postgresql.ENUM(name="logaction").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="language").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="questionstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="userrole").drop(op.get_bind(), checkfirst=True)