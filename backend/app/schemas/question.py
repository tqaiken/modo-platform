from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from app.models.log import LogAction
from app.models.question import (
    CognitiveLevel,
    Language,
    QuestionStatus,
)
from app.schemas.comment import CommentRead
from app.schemas.media import MediaFileRead
from app.schemas.user import UserRead


# ============================================================
# Legacy schemas
# Временно сохраняются для существующих endpoints /questions.
# ============================================================


class QuestionOption(BaseModel):
    text: str = Field(
        min_length=1,
    )

    is_correct: bool = False


class QuestionCreate(BaseModel):
    title: str = Field(
        min_length=5,
        max_length=500,
    )

    body: str = Field(
        min_length=1,
    )

    options: list[QuestionOption] = Field(
        min_length=2,
        max_length=10,
    )

    explanation: Optional[str] = None
    language: Language = Language.RU
    subject_id: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None

    difficulty: int = Field(
        default=1,
        ge=1,
        le=5,
    )


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=500,
    )

    body: Optional[str] = None
    options: Optional[list[QuestionOption]] = None
    explanation: Optional[str] = None
    language: Optional[Language] = None
    subject_id: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None

    difficulty: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
    )


class QuestionSubmit(BaseModel):
    """
    Старый endpoint отправки отдельного вопроса.
    Позже будет заменён отправкой всего варианта.
    """

    pass


class QuestionReview(BaseModel):
    """
    Старая схема проверки отдельного вопроса.
    """

    approved: bool

    comment: str = Field(
        min_length=1,
        max_length=5000,
    )

    edited_title: Optional[str] = None
    edited_body: Optional[str] = None
    edited_options: Optional[list[QuestionOption]] = None
    edited_explanation: Optional[str] = None


# ============================================================
# New bilingual schemas
# Используются для вопросов внутри варианта.
# ============================================================


class BilingualQuestionOption(BaseModel):
    """
    Двуязычный вариант ответа.

    key:
        A, B, C, D и далее при необходимости.
    """

    key: str = Field(
        min_length=1,
        max_length=2,
        pattern=r"^[A-Z]+$",
    )

    text_kz: str = Field(
        min_length=1,
        max_length=5000,
    )

    text_ru: str = Field(
        min_length=1,
        max_length=5000,
    )

    is_correct: bool = False


class VariantQuestionCreate(BaseModel):
    """
    Создание вопроса внутри варианта.

    variant_id, subject_id, author_id и order_number
    определяются backend и не принимаются от frontend.
    """

    learning_objective_id: int = Field(
        ge=1,
    )

    cognitive_level: CognitiveLevel

    resource_kz: str | None = Field(
        default=None,
        max_length=50000,
    )

    resource_ru: str | None = Field(
        default=None,
        max_length=50000,
    )

    question_text_kz: str = Field(
        min_length=1,
        max_length=50000,
    )

    question_text_ru: str = Field(
        min_length=1,
        max_length=50000,
    )

    options: list[BilingualQuestionOption] = Field(
        min_length=4,
        max_length=10,
    )

    explanation_kz: str | None = Field(
        default=None,
        max_length=50000,
    )

    explanation_ru: str | None = Field(
        default=None,
        max_length=50000,
    )

    @model_validator(mode="after")
    def validate_options(self):
        option_keys = [
            option.key
            for option in self.options
        ]

        if len(option_keys) != len(set(option_keys)):
            raise ValueError(
                "Обозначения вариантов ответа должны быть уникальными."
            )

        correct_options = [
            option
            for option in self.options
            if option.is_correct
        ]

        if len(correct_options) != 1:
            raise ValueError(
                "Должен быть выбран ровно один правильный ответ."
            )

        return self


class VariantQuestionUpdate(BaseModel):
    """
    Изменение вопроса внутри варианта.

    Все поля необязательные, поскольку используется PATCH.
    """

    learning_objective_id: int | None = Field(
        default=None,
        ge=1,
    )

    cognitive_level: CognitiveLevel | None = None

    resource_kz: str | None = Field(
        default=None,
        max_length=50000,
    )

    resource_ru: str | None = Field(
        default=None,
        max_length=50000,
    )

    question_text_kz: str | None = Field(
        default=None,
        min_length=1,
        max_length=50000,
    )

    question_text_ru: str | None = Field(
        default=None,
        min_length=1,
        max_length=50000,
    )

    options: list[BilingualQuestionOption] | None = Field(
        default=None,
        min_length=4,
        max_length=10,
    )

    explanation_kz: str | None = Field(
        default=None,
        max_length=50000,
    )

    explanation_ru: str | None = Field(
        default=None,
        max_length=50000,
    )

    @model_validator(mode="after")
    def validate_options(self):
        if self.options is None:
            return self

        option_keys = [
            option.key
            for option in self.options
        ]

        if len(option_keys) != len(set(option_keys)):
            raise ValueError(
                "Обозначения вариантов ответа должны быть уникальными."
            )

        correct_options = [
            option
            for option in self.options
            if option.is_correct
        ]

        if len(correct_options) != 1:
            raise ValueError(
                "Должен быть выбран ровно один правильный ответ."
            )

        return self


class VariantQuestionRead(BaseModel):
    id: int
    variant_id: int | None
    order_number: int

    learning_objective_id: int | None
    cognitive_level: CognitiveLevel | None

    resource_kz: str | None
    resource_ru: str | None

    question_text_kz: str | None
    question_text_ru: str | None

    options: list[dict]

    explanation_kz: str | None
    explanation_ru: str | None

    subject_id: int | None
    status: QuestionStatus

    author_id: int
    reviewer_id: int | None

    media_files: list[MediaFileRead] = Field(
        default_factory=list,
    )

    comments: list[CommentRead] = Field(
        default_factory=list,
    )

    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    reviewed_at: datetime | None
    approved_at: datetime | None

    model_config = {
        "from_attributes": True,
    }


class VariantQuestionList(BaseModel):
    items: list[VariantQuestionRead]
    total: int


# ============================================================
# Legacy read schemas
# ============================================================


class QuestionRead(BaseModel):
    id: int
    title: str
    body: str
    body_html: Optional[str] = None

    options: list[dict]

    explanation: Optional[str] = None
    language: Language = Language.RU
    subject_id: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: int
    status: QuestionStatus

    author: UserRead
    reviewer: Optional[UserRead] = None

    media_files: list[MediaFileRead] = Field(
        default_factory=list,
    )

    comments: list[CommentRead] = Field(
        default_factory=list,
    )

    logs: list["LogRead"] = Field(
        default_factory=list,
    )

    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
    }


class QuestionList(BaseModel):
    items: list[QuestionRead]
    total: int
    page: int
    page_size: int


class LogRead(BaseModel):
    id: int
    action: LogAction
    details: Optional[str] = None
    user: UserRead
    timestamp: datetime

    model_config = {
        "from_attributes": True,
    }