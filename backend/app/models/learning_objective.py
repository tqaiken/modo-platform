from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class LearningObjective(Base):
    """
    Ожидаемый результат обучения, ОРО.

    Каждый ОРО относится к конкретному предмету.
    Разработчик выбирает ОРО только из списка,
    доступного для предмета своей учётной записи.
    """

    __tablename__ = "learning_objectives"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    subject_id = Column(
        Integer,
        ForeignKey(
            "subjects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    code = Column(
        String(100),
        nullable=False,
        index=True,
    )

    title_kz = Column(
        Text,
        nullable=False,
    )

    title_ru = Column(
        Text,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    subject = relationship(
        "Subject",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<LearningObjective "
            f"id={self.id} "
            f"subject_id={self.subject_id} "
            f"code='{self.code}'>"
        )