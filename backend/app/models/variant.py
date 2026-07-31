import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class VariantStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VERIFICATION = "VERIFICATION"
    REVISION = "REVISION"
    APPROVED = "APPROVED"
    IN_BANK = "IN_BANK"


class Variant(Base):
    __tablename__ = "variants"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String(500),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=True,
    )

    subject = relationship(
        "Subject",
        lazy="joined",
    )

    developer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    developer = relationship(
        "User",
        foreign_keys=[developer_id],
        lazy="joined",
    )

    questions = relationship(
        "Question",
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="Question.order_number",
        lazy="selectin",
    )

    status = Column(
        Enum(VariantStatus),
        default=VariantStatus.DRAFT,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    submitted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self):
        return (
            f"<Variant #{self.id} "
            f"[{self.status.value}] "
            f"'{self.title[:40]}'>"
        )