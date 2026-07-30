from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    question = relationship("Question", back_populates="comments")

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", lazy="joined")

    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<ReviewComment #{self.id} on Q#{self.question_id}>"
