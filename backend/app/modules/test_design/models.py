"""
Test Design module — blueprint, шаблоны диагностик, генерация вариантов.
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


class BlueprintStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DiagnosticStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# ─── Blueprint ────────────────────────────────────────────────────────────────

class Blueprint(Base):
    """
    Blueprint — матрица комплектации диагностики.
    Определяет: раздел × цель × компетенция × когнитивный уровень × сложность × кол-во заданий.
    """
    __tablename__ = "blueprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    name_kz: Mapped[str | None] = mapped_column(String(255))
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id"), index=True
    )
    grade: Mapped[int] = mapped_column(Integer)
    academic_year: Mapped[str] = mapped_column(String(9))
    status: Mapped[BlueprintStatus] = mapped_column(
        Enum(BlueprintStatus), default=BlueprintStatus.DRAFT
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cells = relationship("BlueprintCell", back_populates="blueprint", cascade="all, delete-orphan")
    diagnostics = relationship("Diagnostic", back_populates="blueprint")


class BlueprintCell(Base):
    """Отдельная ячейка blueprint-матрицы."""
    __tablename__ = "blueprint_cells"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprints.id"), index=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id")
    )
    objective_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_objectives.id")
    )
    competency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competencies.id")
    )
    cognitive_level: Mapped[str] = mapped_column(String(30))
    difficulty: Mapped[str] = mapped_column(String(20))
    question_count: Mapped[int] = mapped_column(Integer)

    blueprint = relationship("Blueprint", back_populates="cells")


# ─── Diagnostic ───────────────────────────────────────────────────────────────

class Diagnostic(Base):
    """Шаблон диагностики — назначается администратором."""
    __tablename__ = "diagnostics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    name_kz: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprints.id"), index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id")
    )
    grade: Mapped[int] = mapped_column(Integer)

    # Настройки сессии
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True)

    # Количество вариантов
    variant_count: Mapped[int] = mapped_column(Integer, default=1)

    status: Mapped[DiagnosticStatus] = mapped_column(
        Enum(DiagnosticStatus), default=DiagnosticStatus.DRAFT
    )

    # Назначение
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    assigned_class_ids: Mapped[list | None] = mapped_column(JSON)  # [class_id, ...]

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    blueprint = relationship("Blueprint", back_populates="diagnostics")
    variants = relationship("DiagnosticVariant", back_populates="diagnostic", cascade="all, delete-orphan")


class DiagnosticVariant(Base):
    """Сгенерированный вариант диагностики."""
    __tablename__ = "diagnostic_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diagnostic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostics.id"), index=True
    )
    variant_number: Mapped[int] = mapped_column(Integer)
    questions_order: Mapped[list] = mapped_column(JSON)  # [question_id, ...]
    options_order: Mapped[dict | None] = mapped_column(JSON)  # {question_id: [option_order]}

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    diagnostic = relationship("Diagnostic", back_populates="variants")
