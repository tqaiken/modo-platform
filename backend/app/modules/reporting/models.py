"""
Reporting module — отчёты, сертификаты, QR-проверка.
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
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReportType(str, enum.Enum):
    STUDENT = "student"
    CLASS = "class"
    SCHOOL = "school"


class CertificateType(str, enum.Enum):
    STUDENT = "student"
    SCHOOL = "school"
    EXPERT = "expert"


class Report(Base):
    """Сгенерированный отчёт."""
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType))
    diagnostic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostics.id"), index=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True
    )  # student_id, class_id, или organization_id
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Файл
    file_format: Mapped[str] = mapped_column(String(10))  # pdf, xlsx, csv
    storage_key: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(Integer)

    # Содержание (для API)
    data: Mapped[dict | None] = mapped_column(JSON)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    diagnostic = relationship("Diagnostic")
    organization = relationship("Organization")


class Certificate(Base):
    """Сертификат с QR-проверкой."""
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    certificate_type: Mapped[CertificateType] = mapped_column(Enum(CertificateType))
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True
    )  # student_id или organization_id
    diagnostic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostics.id")
    )

    # QR-хеш для верификации
    qr_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    verification_url: Mapped[str] = mapped_column(String(500))

    # Данные сертификата
    holder_name: Mapped[str] = mapped_column(String(255))
    holder_name_kz: Mapped[str | None] = mapped_column(String(255))
    subject_name: Mapped[str] = mapped_column(String(255))
    score_display: Mapped[str] = mapped_column(String(50))  # "85%"
    level: Mapped[str] = mapped_column(String(50))

    # Файл
    storage_key: Mapped[str | None] = mapped_column(String(500))

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    issued_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    diagnostic = relationship("Diagnostic")
