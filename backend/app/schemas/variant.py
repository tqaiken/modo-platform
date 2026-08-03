from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.models.variant import VariantStatus


class VariantCreate(BaseModel):
    """
    Создание варианта разработчиком.

    Предмет и разработчик определяются backend
    по текущей учётной записи.
    """

    title: str = Field(
        min_length=2,
        max_length=500,
        description="Название или код варианта",
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("title")
    @classmethod
    def normalize_title(
        cls,
        value: str,
    ) -> str:
        return value.strip()

    @field_validator(
        "description",
        mode="before",
    )
    @classmethod
    def normalize_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        return normalized or None


class VariantUpdate(BaseModel):
    """
    Изменение названия или описания варианта.

    Предмет, разработчик и статус
    не принимаются от frontend.
    """

    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=500,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("title")
    @classmethod
    def normalize_title(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip()

    @field_validator(
        "description",
        mode="before",
    )
    @classmethod
    def normalize_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        return normalized or None


class VariantReview(BaseModel):
    """
    Итоговое решение верификатора
    по всему варианту.

    approved=True:
        VERIFICATION -> APPROVED

    approved=False:
        VERIFICATION -> REVISION
    """

    approved: bool

    comment: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator("comment")
    @classmethod
    def normalize_comment(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Комментарий к проверке обязателен."
            )

        return normalized


class VariantRead(BaseModel):
    """
    Основное представление варианта.

    Используется в кабинете разработчика
    и после изменения статуса.
    """

    id: int
    title: str
    description: str | None

    subject_id: int | None
    developer_id: int

    reviewer_id: int | None = None
    reviewer_name: str | None = None
    review_comment: str | None = None

    status: VariantStatus
    question_count: int = 0

    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    reviewed_at: datetime | None
    approved_at: datetime | None

    model_config = {
        "from_attributes": True,
    }


class VariantList(BaseModel):
    """
    Постраничный список вариантов разработчика.
    """

    items: list[VariantRead]
    total: int
    page: int
    page_size: int


class VariantQueueItem(BaseModel):
    """
    Краткие данные варианта
    в очереди верификатора.
    """

    id: int
    title: str
    description: str | None

    subject_id: int | None

    developer_id: int
    developer_name: str

    status: VariantStatus
    question_count: int = 0

    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    reviewed_at: datetime | None
    approved_at: datetime | None

    model_config = {
        "from_attributes": True,
    }


class VariantQueueList(BaseModel):
    """
    Постраничная очередь вариантов
    со статусом VERIFICATION.
    """

    items: list[VariantQueueItem]
    total: int
    page: int
    page_size: int


class VariantReviewResult(BaseModel):
    """
    Результат утверждения варианта
    или возврата на доработку.
    """

    id: int
    title: str
    status: VariantStatus

    reviewer_id: int | None
    reviewer_name: str | None
    review_comment: str | None

    question_count: int

    submitted_at: datetime | None
    reviewed_at: datetime | None
    approved_at: datetime | None

    model_config = {
        "from_attributes": True,
    }


class VariantDashboard(BaseModel):
    """
    Показатели кабинета разработчика.
    """

    total_variants: int
    draft_variants: int
    verification_variants: int
    revision_variants: int
    approved_variants: int
    bank_variants: int
    total_questions: int