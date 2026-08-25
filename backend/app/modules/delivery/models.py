"""
Delivery module — сессии тестирования, таймер, ответы, синхронизация.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionStatus(str, enum.Enum):
    PENDING = "pending"          # Ожидает начала
    ACTIVE = "active"            # В процессе
    PAUSED = "paused"            # Приостановлена
    SUBMITTED = "submitted"      # Отправлена на проверку
    GRADED = "graded"            # Проверена
    CANCELLED = "cancelled"      # Отменена


class AnswerStatus(str, enum.Enum):
    DRAFT = "draft"              # Черновик (локально)
    SYNCED = "synced"            # Синхронизирован с сервером
    SUBMITTED = "submitted"      # Финально отправлена
    GRADED = "graded"            # Проверена


# ─── TestSession ──────────────────────────────────────────────────────────────

class TestSession(Base):
    """Сессия прохождения диагностики учеником."""
    __tablename__ = "test_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diagnostic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostics.id"), index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostic_variants.id")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # Доступ
    access_code: Mapped[str] = mapped_column(String(10), unique=True)  # Одноразовый код
    access_code_used: Mapped[bool] = mapped_column(Boolean, default=False)

    # Таймер
    time_limit_minutes: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Статус
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.PENDING
    )

    # Специальные условия (доп. время, масштаб и т.д.)
    special_conditions: Mapped[dict | None] = mapped_column(JSON)

    # Метаданные
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    diagnostic = relationship("Diagnostic")
    variant = relationship("DiagnosticVariant")
    student = relationship("User")
    answers = relationship("Answer", back_populates="session", cascade="all, delete-orphan")


# ─── Answer ───────────────────────────────────────────────────────────────────

class Answer(Base):
    """Ответ ученика на задание."""
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_sessions.id"), index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), index=True
    )

    # Ответ
    answer_data: Mapped[dict | None] = mapped_column(JSON)  # Формат зависит от типа
    # single_choice: {"selected": "A"}
    # multiple_choice: {"selected": ["A", "C"]}
    # matching: {"pairs": [{"left": 1, "right": 3}, ...]}
    # sequence: {"order": [3, 1, 2, 4]}
    # short_answer: {"text": "42"}
    # extended_answer: {"text": "Развёрнутый ответ..."}

    # Статус
    status: Mapped[AnswerStatus] = mapped_column(
        Enum(AnswerStatus), default=AnswerStatus.DRAFT
    )

    # Номер задания в варианте
    question_number: Mapped[int] = mapped_column(Integer)

    # Метаданные синхронизации
    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session = relationship("TestSession", back_populates="answers")
    question = relationship("Question")
    review = relationship("AnswerReview", back_populates="answer", uselist=False)


# ─── AnswerReview ─────────────────────────────────────────────────────────────

class AnswerReview(Base):
    """Проверка ответа (для развёрнутых ответов — ручная)."""
    __tablename__ = "answer_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("answers.id"), unique=True, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    score: Mapped[float] = mapped_column()
    max_score: Mapped[float] = mapped_column()
    comment: Mapped[str | None] = mapped_column(Text)
    is_auto: Mapped[bool] = mapped_column(Boolean, default=False)

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    answer = relationship("Answer", back_populates="review")
    reviewer = relationship("User")
