"""
Item Bank module — задания, версии, метаданные, жизненный цикл.
Расширение существующей модели Question из TestForge.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class QuestionStatus(str, enum.Enum):
    """Расширенный жизненный цикл задания."""
    DRAFT = "draft"                           # Черновик
    SUBJECT_REVIEW = "subject_review"         # Предметная экспертиза
    METHOD_REVIEW = "method_review"           # Методическая экспертиза
    TECH_REVIEW = "tech_review"               # Техническая проверка
    APPROVED = "approved"                     # Утверждено → в банк
    PILOT = "pilot"                           # Апробация
    CALIBRATED = "calibrated"                 # После стат. анализа
    ARCHIVED = "archived"                     # Архив


class QuestionType(str, enum.Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    MATCHING = "matching"
    SEQUENCE = "sequence"
    SHORT_ANSWER = "short_answer"
    EXTENDED_ANSWER = "extended_answer"
    FILL_BLANK = "fill_blank"


class Difficulty(str, enum.Enum):
    BASIC = "basic"
    MEDIUM = "medium"
    HIGH = "high"


class CognitiveLevel(str, enum.Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class Language(str, enum.Enum):
    RU = "ru"
    KZ = "kz"


class AccessLevel(str, enum.Enum):
    """Уровень допуска к заданию."""
    PUBLIC = "public"
    RESTRICTED = "restricted"
    CLASSIFIED = "classified"


# ─── Subject & Section ────────────────────────────────────────────────────────

class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(20), unique=True)  # "MATH_9"
    name_ru: Mapped[str] = mapped_column(String(255))
    name_kz: Mapped[str] = mapped_column(String(255))
    grade: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sections = relationship("Section", back_populates="subject", cascade="all, delete-orphan")


class Section(Base):
    """Раздел предмета (напр. 'Алгебра', 'Геометрия')."""
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(50))
    name_ru: Mapped[str] = mapped_column(String(255))
    name_kz: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    subject = relationship("Subject", back_populates="sections")


# ─── Learning Objective & Competency ──────────────────────────────────────────

class LearningObjective(Base):
    """Цель обучения (ОРО)."""
    __tablename__ = "learning_objectives"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(50))
    description_ru: Mapped[str] = mapped_column(Text)
    description_kz: Mapped[str] = mapped_column(Text)

    section = relationship("Section")
    competencies = relationship("Competency", back_populates="objective")


class Competency(Base):
    """Компетенция, связанная с целью обучения."""
    __tablename__ = "competencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_objectives.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(50))
    name_ru: Mapped[str] = mapped_column(String(255))
    name_kz: Mapped[str] = mapped_column(String(255))

    objective = relationship("LearningObjective", back_populates="competencies")


# ─── Question ─────────────────────────────────────────────────────────────────

class Question(Base):
    """Расширенное задание BAGALAU."""
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Содержание
    text: Mapped[str] = mapped_column(Text)
    text_kz: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    explanation_kz: Mapped[str | None] = mapped_column(Text)

    # Тип и формат
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType))
    options: Mapped[dict | None] = mapped_column(JSON)  # {"A": "...", "B": "...", ...}
    options_kz: Mapped[dict | None] = mapped_column(JSON)
    correct_answer: Mapped[dict | None] = mapped_column(JSON)  # {"answer": "A"} или {"A": true, "C": true}
    matching_pairs: Mapped[dict | None] = mapped_column(JSON)
    sequence_answer: Mapped[list | None] = mapped_column(JSON)
    rubric: Mapped[dict | None] = mapped_column(JSON)  # Рубрика для развёрнутого ответа

    # Blueprint-метаданные
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id"), index=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id"), index=True
    )
    objective_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_objectives.id"), index=True
    )
    competency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competencies.id"), index=True
    )
    cognitive_level: Mapped[CognitiveLevel] = mapped_column(
        Enum(CognitiveLevel), default=CognitiveLevel.UNDERSTAND
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty), default=Difficulty.MEDIUM
    )

    # Язык и версионирование
    language: Mapped[Language] = mapped_column(Enum(Language), default=Language.RU)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id")
    )

    # Статус и доступ
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus), default=QuestionStatus.DRAFT
    )
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel), default=AccessLevel.RESTRICTED
    )

    # Автор
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Статистика (после апробации)
    difficulty_index: Mapped[float | None] = mapped_column(Float)  # p-value
    discrimination_index: Mapped[float | None] = mapped_column(Float)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    subject = relationship("Subject")
    section = relationship("Section")
    objective = relationship("LearningObjective")
    competency = relationship("Competency")
    media_files = relationship("MediaFile", back_populates="question", cascade="all, delete-orphan")
    review_comments = relationship("ReviewComment", back_populates="question", cascade="all, delete-orphan")


class MediaFile(Base):
    """Медиафайлы задания."""
    __tablename__ = "media_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(500))  # R2/Supabase key
    watermark: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question = relationship("Question", back_populates="media_files")


class ReviewComment(Base):
    """Комментарии экспертизы."""
    __tablename__ = "review_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    review_type: Mapped[str] = mapped_column(String(50))  # subject | method | tech
    comment: Mapped[str] = mapped_column(Text)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question = relationship("Question", back_populates="review_comments")
