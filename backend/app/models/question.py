import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Enum, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Language(str, enum.Enum):
    RU = "ru"
    KZ = "kz"


class QuestionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VERIFICATION = "VERIFICATION"
    REVISION = "REVISION"
    IN_BANK = "IN_BANK"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)           # supports LaTeX $...$
    body_html = Column(Text, nullable=True)        # pre-rendered HTML+KaTeX
    options = Column(JSON, nullable=False)         # list of {text, is_correct}
    explanation = Column(Text, nullable=True)      # answer explanation
    language = Column(Enum(Language), default=Language.RU, nullable=False)

    # Subject FK (normalized) + legacy string field
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    subject_rel = relationship("Subject", lazy="joined")
    subject = Column(String(255), nullable=True)   # kept for backward compat
    topic = Column(String(255), nullable=True)
    difficulty = Column(Integer, default=1)        # 1-5
    status = Column(
        Enum(QuestionStatus),
        default=QuestionStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # ── Ownership ──
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", foreign_keys=[author_id], lazy="joined")

    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer = relationship("User", foreign_keys=[reviewer_id], lazy="joined")

    # ── Relations ──
    media_files = relationship("MediaFile", back_populates="question", cascade="all, delete-orphan")
    comments = relationship("ReviewComment", back_populates="question", cascade="all, delete-orphan")
    logs = relationship("QuestionLog", back_populates="question", cascade="all, delete-orphan")

    # ── Timestamps ──
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
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Question #{self.id} [{self.status.value}] '{self.title[:40]}'>"
