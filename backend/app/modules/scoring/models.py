"""
Scoring module — ключи ответов, рубрики, расчёт результатов.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScoringKey(Base):
    """Ключ ответа (для автоматической проверки)."""
    __tablename__ = "scoring_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), unique=True, index=True
    )
    correct_answer: Mapped[dict] = mapped_column(JSON)
    max_score: Mapped[float] = mapped_column(Float, default=1.0)
    scoring_rules: Mapped[dict | None] = mapped_column(JSON)
    # Пример scoring_rules для multiple_choice:
    # {"partial_credit": true, "penalty_per_wrong": -0.25}

    question = relationship("Question")


class Rubric(Base):
    """Рубрика для развёрнутого ответа."""
    __tablename__ = "rubrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), unique=True, index=True
    )
    max_score: Mapped[float] = mapped_column(Float)
    criteria: Mapped[list] = mapped_column(JSON)
    # Пример criteria:
    # [
    #   {"name": "Понимание", "max_score": 3, "levels": [
    #     {"score": 3, "description": "Полное понимание"},
    #     {"score": 2, "description": "Частичное"},
    #     {"score": 1, "description": "Минимальное"},
    #     {"score": 0, "description": "Отсутствует"}
    #   ]},
    #   ...
    # ]

    question = relationship("Question")


class Result(Base):
    """Результат диагностики ученика."""
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_sessions.id"), unique=True, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    diagnostic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostics.id"), index=True
    )

    # Общие баллы
    total_score: Mapped[float] = mapped_column(Float)
    max_score: Mapped[float] = mapped_column(Float)
    percentage: Mapped[float] = mapped_column(Float)

    # Уровень
    level: Mapped[str] = mapped_column(String(50))  # "Высокий", "Средний", "Базовый", "Ниже базового"

    # Аналитика по компетенциям
    competency_scores: Mapped[dict | None] = mapped_column(JSON)
    # {"COMP_1": {"score": 5, "max": 8, "pct": 62.5, "level": "Средний"}, ...}

    # Аналитика по разделам
    section_scores: Mapped[dict | None] = mapped_column(JSON)
    # {"ALGEBRA": {"score": 12, "max": 15, "pct": 80}, ...}

    # Классические показатели
    # (для агрегации на уровне класса/школы)

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session = relationship("TestSession")
    student = relationship("User")
    diagnostic = relationship("Diagnostic")
