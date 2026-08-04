import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
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
        ForeignKey(
            "subjects.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    subject = relationship(
        "Subject",
        lazy="joined",
    )

    # ========================================================
    # Developer
    # ========================================================

    developer_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    developer = relationship(
        "User",
        foreign_keys=[developer_id],
        lazy="joined",
    )

    # ========================================================
    # Verifier
    # ========================================================

    reviewer_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    reviewer = relationship(
        "User",
        foreign_keys=[reviewer_id],
        lazy="joined",
    )

    review_comment = Column(
        Text,
        nullable=True,
    )

    # ========================================================
    # Curator
    # ========================================================

    curator_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    curator = relationship(
        "User",
        foreign_keys=[curator_id],
        lazy="joined",
    )

    curator_comment = Column(
        Text,
        nullable=True,
    )

    # ========================================================
    # Questions
    # ========================================================

    questions = relationship(
        "Question",
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="Question.order_number",
        lazy="selectin",
    )

    # ========================================================
    # Status
    # ========================================================

    status = Column(
        Enum(
            VariantStatus,
            name="variantstatus",
        ),
        default=VariantStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # ========================================================
    # Dates
    # ========================================================

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        onupdate=lambda: datetime.now(
            timezone.utc
        ),
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

    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        status_value = (
            self.status.value
            if self.status is not None
            else "UNKNOWN"
        )

        title_preview = (
            self.title[:40]
            if self.title
            else ""
        )

        return (
            f"<Variant id={self.id} "
            f"status={status_value} "
            f"title='{title_preview}'>"
        )