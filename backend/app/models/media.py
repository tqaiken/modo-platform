from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    question = relationship("Question", back_populates="media_files")

    original_filename = Column(String(500), nullable=False)
    r2_key = Column(String(1000), nullable=False, unique=True)  # path in R2 bucket
    content_type = Column(String(100), nullable=False)           # image/png, image/jpeg, etc.
    file_size = Column(BigInteger, nullable=False)               # bytes
    width = Column(Integer, nullable=True)                       # px (for images)
    height = Column(Integer, nullable=True)                      # px (for images)

    public_url = Column(String(2000), nullable=False)            # full public URL

    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<MediaFile #{self.id} {self.original_filename}>"
