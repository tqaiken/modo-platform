import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
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


class CognitiveLevel(str, enum.Enum):
    BASIC = "BASIC"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Question(Base):
    __tablename__ = "questions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Вариант, внутри которого находится вопрос.
    # nullable=True временно сохраняет совместимость
    # со старыми вопросами без варианта.
    variant_id = Column(
        Integer,
        ForeignKey(
            "variants.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    variant = relationship(
        "Variant",
        back_populates="questions",
        lazy="joined",
    )

    # Порядковый номер вопроса внутри варианта.
    order_number = Column(
        Integer,
        nullable=False,
        default=1,
    )

    # Ожидаемый результат обучения.
    learning_objective_id = Column(
        Integer,
        ForeignKey(
            "learning_objectives.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    learning_objective = relationship(
        "LearningObjective",
        lazy="joined",
    )

    # Уровень когнитивных навыков:
    # BASIC  = Базовый: знание, понимание
    # MEDIUM = Средний: применение, анализ
    # HIGH   = Высокий: синтез, оценка
    cognitive_level = Column(
        Enum(
            CognitiveLevel,
            name="cognitivelevel",
        ),
        nullable=True,
        index=True,
    )

    # Блок ресурсов: текст, график, рисунок,
    # таблица, схема и другие материалы.
    # Содержимое хранится как Markdown + LaTeX.
    resource_kz = Column(
        Text,
        nullable=True,
    )

    resource_ru = Column(
        Text,
        nullable=True,
    )

    # Текст вопроса на двух языках.
    # Содержимое хранится как Markdown + LaTeX.
    question_text_kz = Column(
        Text,
        nullable=True,
    )

    question_text_ru = Column(
        Text,
        nullable=True,
    )

    # Варианты ответа хранятся в двуязычной структуре:
    #
    # [
    #   {
    #     "key": "A",
    #     "text_kz": "...",
    #     "text_ru": "...",
    #     "is_correct": false
    #   },
    #   ...
    # ]
    #
    # API будет требовать минимум четыре варианта.
    options = Column(
        JSON,
        nullable=False,
        default=list,
    )

    # Пояснение правильного ответа.
    explanation_kz = Column(
        Text,
        nullable=True,
    )

    explanation_ru = Column(
        Text,
        nullable=True,
    )

    # Предмет копируется из варианта и аккаунта
    # разработчика. Разработчик не выбирает его вручную.
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=True,
        index=True,
    )

    subject_rel = relationship(
        "Subject",
        lazy="joined",
    )

    status = Column(
        Enum(
            QuestionStatus,
            name="questionstatus",
        ),
        default=QuestionStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Автор вопроса.
    author_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    author = relationship(
        "User",
        foreign_keys=[author_id],
        lazy="joined",
    )

    # Верификатор вопроса.
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    reviewer = relationship(
        "User",
        foreign_keys=[reviewer_id],
        lazy="joined",
    )

    # Связанные файлы, комментарии и история.
    media_files = relationship(
        "MediaFile",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    comments = relationship(
        "ReviewComment",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    logs = relationship(
        "QuestionLog",
        back_populates="question",
        cascade="all, delete-orphan",
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

    # Старые поля временно сохраняются.
    # Они нужны до завершения миграции существующих
    # записей и старых endpoints.
    title = Column(
        String(500),
        nullable=False,
        default="Вопрос",
    )

    body = Column(
        Text,
        nullable=False,
        default="",
    )

    body_html = Column(
        Text,
        nullable=True,
    )

    explanation = Column(
        Text,
        nullable=True,
    )

    language = Column(
        Enum(
            Language,
            name="language",
        ),
        default=Language.RU,
        nullable=False,
    )

    subject = Column(
        String(255),
        nullable=True,
    )

    topic = Column(
        String(255),
        nullable=True,
    )

    difficulty = Column(
        Integer,
        default=1,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Question id={self.id} "
            f"variant_id={self.variant_id} "
            f"order={self.order_number} "
            f"status={self.status.value}>"
        )