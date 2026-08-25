"""
Organizations module — иерархия школ, классы, привязка к регионам.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrgType(str, enum.Enum):
    SCHOOL = "school"
    DISTRICT = "district"
    REGION = "region"
    NATIONAL = "national"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    name_kz: Mapped[str | None] = mapped_column(String(255))  # Казахское название
    bin_number: Mapped[str | None] = mapped_column(String(12), unique=True)  # БИН
    org_type: Mapped[OrgType] = mapped_column(Enum(OrgType), default=OrgType.SCHOOL)
    language: Mapped[str] = mapped_column(String(5), default="ru")

    # Иерархия
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Контакты
    region: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))

    # Метаданные
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    parent = relationship("Organization", remote_side=[id], backref="children")
    users = relationship("User", back_populates="organization")
    classes = relationship("SchoolClass", back_populates="organization", cascade="all, delete-orphan")


class SchoolClass(Base):
    """Классы внутри школы."""
    __tablename__ = "school_classes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    grade: Mapped[int] = mapped_column(Integer)  # 1–11
    letter: Mapped[str] = mapped_column(String(5))  # "А", "Б", "В"
    academic_year: Mapped[str] = mapped_column(String(9))  # "2026-2027"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization = relationship("Organization", back_populates="classes")
    students = relationship("StudentProfile", back_populates="school_class")


class StudentProfile(Base):
    """Профиль ученика (связь User → Class)."""
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("school_classes.id"), index=True
    )
    student_number: Mapped[str | None] = mapped_column(String(20))  # Условный номер

    school_class = relationship("SchoolClass", back_populates="students")
    user = relationship("User")
