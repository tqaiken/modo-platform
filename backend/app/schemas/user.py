from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.user import UserRole


SUBJECT_REQUIRED_ROLES = {
    UserRole.DEVELOPER,
    UserRole.VERIFIER,
}


def normalize_username(value: str) -> str:
    """
    Нормализует логин:
    - удаляет пробелы по краям;
    - переводит в нижний регистр.
    """
    return value.strip().lower()


class UserCreate(BaseModel):
    """
    Создание первого SUPER_ADMIN.
    """

    username: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9._-]+$",
    )

    email: EmailStr | None = None

    full_name: str = Field(
        min_length=2,
        max_length=255,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: UserRole = UserRole.SUPER_ADMIN

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_optional_email(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()

        return normalized or None


class UserCreateByAdmin(BaseModel):
    """
    Создание пользователя супер-администратором.
    """

    username: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9._-]+$",
    )

    email: EmailStr | None = None

    full_name: str = Field(
        min_length=2,
        max_length=255,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: UserRole

    subject_id: int | None = Field(
        default=None,
        ge=1,
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_optional_email(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()

        return normalized or None

    @model_validator(mode="after")
    def validate_subject_assignment(self):
        if (
            self.role in SUBJECT_REQUIRED_ROLES
            and self.subject_id is None
        ):
            raise ValueError(
                "Предмет обязателен для разработчика "
                "и верификатора."
            )

        if (
            self.role not in SUBJECT_REQUIRED_ROLES
            and self.subject_id is not None
        ):
            raise ValueError(
                "Предмет можно назначать только "
                "разработчику или верификатору."
            )

        return self


class UserUpdateByAdmin(BaseModel):
    """
    Изменение существующего пользователя SUPER_ADMIN.

    Все поля необязательные, поскольку используется PATCH.
    Чтобы удалить email, нужно передать email: null.
    """

    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9._-]+$",
    )

    email: EmailStr | None = None

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )

    role: UserRole | None = None

    subject_id: int | None = Field(
        default=None,
        ge=1,
    )

    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def validate_username(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return normalize_username(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_optional_email(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()

        return normalized or None


class UserLogin(BaseModel):
    """
    Авторизация по логину и паролю.
    """

    username: str = Field(
        min_length=3,
        max_length=100,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return normalize_username(value)


class UserRead(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str
    role: UserRole
    is_active: bool
    subject_id: int | None

    model_config = {
        "from_attributes": True,
    }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead