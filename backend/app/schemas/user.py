from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    model_validator,
)

from app.models.user import UserRole


SUBJECT_REQUIRED_ROLES = {
    UserRole.DEVELOPER,
    UserRole.VERIFIER,
}


class UserCreate(BaseModel):
    """
    Используется только для создания первого SUPER_ADMIN.
    """

    email: EmailStr

    full_name: str = Field(
        min_length=2,
        max_length=255,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: UserRole = UserRole.DEVELOPER


class UserCreateByAdmin(BaseModel):
    """
    Создание пользователя супер-администратором.
    """

    email: EmailStr

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

    Можно изменить имя, роль, предмет, пароль
    и состояние учётной записи.
    """

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


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: str
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