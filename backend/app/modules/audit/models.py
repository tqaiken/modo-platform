"""
Audit module — неизменяемый лог всех действий.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditAction(str, enum.Enum):
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    TOTP_ENABLED = "totp_enabled"
    TOTP_DISABLED = "totp_disabled"
    ROLE_CHANGED = "role_changed"

    # Organizations
    ORG_CREATED = "org_created"
    ORG_UPDATED = "org_updated"
    CLASS_CREATED = "class_created"
    STUDENT_IMPORTED = "student_imported"

    # Questions
    QUESTION_CREATED = "question_created"
    QUESTION_UPDATED = "question_updated"
    QUESTION_STATUS_CHANGED = "question_status_changed"
    QUESTION_VIEWED = "question_viewed"

    # Diagnostics
    DIAGNOSTIC_CREATED = "diagnostic_created"
    DIAGNOSTIC_ACTIVATED = "diagnostic_activated"
    VARIANT_GENERATED = "variant_generated"

    # Sessions
    SESSION_STARTED = "session_started"
    SESSION_SUBMITTED = "session_submitted"
    SESSION_CANCELLED = "session_cancelled"
    ANSWER_SAVED = "answer_saved"
    ANSWER_SYNCED = "answer_synced"

    # Scoring
    RESULT_CALCULATED = "result_calculated"
    REVIEW_COMPLETED = "review_completed"

    # Reports
    REPORT_GENERATED = "report_generated"
    CERTIFICATE_ISSUED = "certificate_issued"

    # Security
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCESS_DENIED = "access_denied"
    DATA_EXPORT = "data_export"


class AuditSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditLog(Base):
    """Неизменяемый аудит-лог."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Кто
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Что
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), index=True)
    severity: Mapped[AuditSeverity] = mapped_column(
        Enum(AuditSeverity), default=AuditSeverity.INFO
    )
    entity_type: Mapped[str | None] = mapped_column(String(50))  # "question", "session", ...
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Детали
    details: Mapped[dict | None] = mapped_column(JSON)
    # Пример: {"old_status": "draft", "new_status": "subject_review"}

    # Контекст
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Время (неизменяемое)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User")
    organization = relationship("Organization")
