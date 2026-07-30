import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class LogAction(str, enum.Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"
    EDITED_BY_VERIFIER = "EDITED_BY_VERIFIER"
    STATUS_CHANGED = "STATUS_CHANGED"
    MEDIA_UPLOADED = "MEDIA_UPLOADED"
    MEDIA_DELETED = "MEDIA_DELETED"


class QuestionLog(Base):
    """Immutable audit trail for every action on a question."""
    __tablename__ = "question_logs"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(Enum(LogAction), nullable=False)
    details = Column(Text, nullable=True)  # JSON or free-text description
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relations
    question = relationship("Question", lazy="joined")
    user = relationship("User", lazy="joined")

    def __repr__(self):
        return f"<QuestionLog Q#{self.question_id} {self.action.value} by U#{self.user_id}>"
