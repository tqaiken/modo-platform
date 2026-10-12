from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuestionVersion(Base):
    """
    Неизменяемый снимок состояния вопроса.

    Каждая версия принадлежит одному вопросу и имеет
    последовательный номер в пределах этого вопроса.
    """

    __tablename__ = "question_versions"

    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "version_number",
            name=(
                "uq_question_versions_"
                "question_version"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    question_id = Column(
        Integer,
        ForeignKey(
            "questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    version_number = Column(
        Integer,
        nullable=False,
    )

    snapshot = Column(
        JSON,
        nullable=False,
    )

    change_reason = Column(
        String(255),
        nullable=False,
        default="UPDATED",
    )

    change_details = Column(
        Text,
        nullable=True,
    )

    created_by_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
        index=True,
    )

    question = relationship(
        "Question",
        back_populates="versions",
    )

    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            "<QuestionVersion "
            f"id={self.id} "
            f"question_id={self.question_id} "
            f"version={self.version_number}>"
        )