"""
Analytics module — агрегации, диагностические индексы, сравнения.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClassAnalytics(Base):
    """Агрегированная аналитика по классу."""
    __tablename__ = "class_analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diagnostic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostics.id"), index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("school_classes.id"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Общие показатели
    students_total: Mapped[int] = mapped_column(Integer)
    students_completed: Mapped[int] = mapped_column(Integer)
    average_percentage: Mapped[float] = mapped_column(Float)
    median_percentage: Mapped[float] = mapped_column(Float)
    std_deviation: Mapped[float] = mapped_column(Float)

    # Уровни
    level_distribution: Mapped[dict] = mapped_column(JSON)
    # {"high": 5, "medium": 12, "basic": 8, "below_basic": 2}

    # Группы риска
    at_risk_count: Mapped[int] = mapped_column(Integer, default=0)

    # По разделам
    section_averages: Mapped[dict | None] = mapped_column(JSON)
    # {"ALGEBRA": 72.5, "GEOMETRY": 58.3, ...}

    # По компетенциям
    competency_averages: Mapped[dict | None] = mapped_column(JSON)

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    diagnostic = relationship("Diagnostic")
    school_class = relationship("SchoolClass")
    organization = relationship("Organization")


class SchoolAnalytics(Base):
    """Агрегированная аналитика по школе."""
    __tablename__ = "school_analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diagnostic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostics.id"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Общие показатели
    classes_total: Mapped[int] = mapped_column(Integer)
    students_total: Mapped[int] = mapped_column(Integer)
    students_completed: Mapped[int] = mapped_column(Integer)
    average_percentage: Mapped[float] = mapped_column(Float)

    # Диагностический индекс школы
    diagnostic_index: Mapped[float] = mapped_column(Float)
    # Формула: средневзвешенный % по всем предметам

    # Уровни
    level_distribution: Mapped[dict] = mapped_column(JSON)

    # Сравнение (обезличенное)
    percentile_rank: Mapped[float | None] = mapped_column(Float)

    # Рекомендации (автоматические)
    recommendations: Mapped[list | None] = mapped_column(JSON)
    # [{"area": "Геометрия", "priority": "high", "suggestion": "..."}, ...]

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    diagnostic = relationship("Diagnostic")
    organization = relationship("Organization")
