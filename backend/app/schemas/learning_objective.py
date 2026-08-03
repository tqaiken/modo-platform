from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class LearningObjectiveCreate(BaseModel):
    """
    Создание ожидаемого результата обучения.
    """

    subject_id: int = Field(
        ge=1,
    )

    code: str = Field(
        min_length=1,
        max_length=100,
    )

    title_kz: str = Field(
        min_length=1,
        max_length=5000,
    )

    title_ru: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator("code")
    @classmethod
    def normalize_code(
        cls,
        value: str,
    ) -> str:
        return value.strip()

    @field_validator(
        "title_kz",
        "title_ru",
    )
    @classmethod
    def normalize_title(
        cls,
        value: str,
    ) -> str:
        return value.strip()


class LearningObjectiveUpdate(BaseModel):
    """
    Изменение существующего ОРО.

    Все поля необязательные, поскольку будет
    использоваться PATCH.
    """

    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    title_kz: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )

    title_ru: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )

    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip()

    @field_validator(
        "title_kz",
        "title_ru",
    )
    @classmethod
    def normalize_title(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip()


class LearningObjectiveRead(BaseModel):
    id: int
    subject_id: int
    code: str
    title_kz: str
    title_ru: str
    is_active: bool

    model_config = {
        "from_attributes": True,
    }


class LearningObjectiveList(BaseModel):
    items: list[LearningObjectiveRead]
    total: int