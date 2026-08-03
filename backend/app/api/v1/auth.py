from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.schemas.user import (
    TokenResponse,
    UserCreate,
    UserCreateByAdmin,
    UserUpdateByAdmin,
    UserLogin,
    UserRead,
)


router = APIRouter(prefix="/auth")


SUBJECT_REQUIRED_ROLES = {
    UserRole.DEVELOPER,
    UserRole.VERIFIER,
}


def get_active_subject(
    db: Session,
    subject_id: int,
) -> Subject:
    subject = (
        db.query(Subject)
        .filter(
            Subject.id == subject_id,
            Subject.is_active.is_(True),
        )
        .first()
    )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Активный предмет с указанным ID "
                "не найден."
            ),
        )

    return subject


@router.post(
    "/register",
    status_code=status.HTTP_403_FORBIDDEN,
)
def register_disabled():
    """
    Публичная регистрация отключена.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Публичная регистрация отключена. "
            "Пользователей создаёт SUPER_ADMIN."
        ),
    )


@router.post(
    "/bootstrap-super-admin",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_super_admin(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Создание первого SUPER_ADMIN.

    Endpoint работает только при пустой таблице users.
    """
    existing_user = db.query(User).first()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Создание первого SUPER_ADMIN недоступно, "
                "поскольку пользователи уже существуют."
            ),
        )

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.SUPER_ADMIN,
        subject_id=None,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id)}
    )

    return TokenResponse(
        access_token=token,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user_by_super_admin(
    payload: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создание пользователя супер-администратором.

    Логин обязателен и уникален.
    Email необязателен, но уникален при заполнении.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Создавать пользователей может "
                "только SUPER_ADMIN."
            ),
        )

    existing_username = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if existing_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином уже существует.",
        )

    if payload.email is not None:
        existing_email = (
            db.query(User)
            .filter(User.email == payload.email)
            .first()
        )

        if existing_email is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует.",
            )

    subject_id = None

    if payload.role in SUBJECT_REQUIRED_ROLES:
        if payload.subject_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Предмет обязателен для разработчика "
                    "и верификатора."
                ),
            )

        subject = get_active_subject(
            db,
            payload.subject_id,
        )

        subject_id = subject.id

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        subject_id=subject_id,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserRead.model_validate(user)


@router.get(
    "/users",
    response_model=list[UserRead],
)
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Список пользователей для SUPER_ADMIN.

    Пароли и хеши паролей не возвращаются.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Просматривать пользователей может "
                "только SUPER_ADMIN."
            ),
        )

    users = (
        db.query(User)
        .order_by(User.full_name.asc())
        .all()
    )

    return [
        UserRead.model_validate(user)
        for user in users
    ]


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
)
def update_user_by_super_admin(
    user_id: int,
    payload: UserUpdateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Изменение пользователя супер-администратором.

    Можно изменить:
    - логин;
    - email;
    - ФИО;
    - пароль;
    - роль;
    - предмет;
    - активность аккаунта.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Изменять пользователей может "
                "только SUPER_ADMIN."
            ),
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден.",
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не переданы данные для изменения.",
        )

    if "username" in update_data:
        new_username = update_data["username"]

        duplicate_username = (
            db.query(User)
            .filter(
                User.username == new_username,
                User.id != user.id,
            )
            .first()
        )

        if duplicate_username is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Пользователь с таким логином "
                    "уже существует."
                ),
            )

    if (
        "email" in update_data
        and update_data["email"] is not None
    ):
        new_email = update_data["email"]

        duplicate_email = (
            db.query(User)
            .filter(
                User.email == new_email,
                User.id != user.id,
            )
            .first()
        )

        if duplicate_email is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Пользователь с таким email "
                    "уже существует."
                ),
            )

    effective_role = update_data.get(
        "role",
        user.role,
    )

    if "subject_id" in update_data:
        effective_subject_id = update_data["subject_id"]
    else:
        effective_subject_id = user.subject_id

    if effective_role in SUBJECT_REQUIRED_ROLES:
        if effective_subject_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Предмет обязателен для разработчика "
                    "и верификатора."
                ),
            )

        subject = get_active_subject(
            db,
            effective_subject_id,
        )

        effective_subject_id = subject.id
    else:
        effective_subject_id = None

    if (
        user.id == current_user.id
        and update_data.get("is_active") is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "SUPER_ADMIN не может отключить "
                "собственную учётную запись."
            ),
        )

    if (
        user.id == current_user.id
        and effective_role != UserRole.SUPER_ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "SUPER_ADMIN не может изменить "
                "собственную роль."
            ),
        )

    if "username" in update_data:
        user.username = update_data["username"]

    if "email" in update_data:
        user.email = update_data["email"]

    if "full_name" in update_data:
        user.full_name = update_data["full_name"]

    if "password" in update_data:
        user.hashed_password = hash_password(
            update_data["password"]
        )

    if "role" in update_data:
        user.role = effective_role

    if "is_active" in update_data:
        user.is_active = update_data["is_active"]

    user.subject_id = effective_subject_id

    db.commit()
    db.refresh(user)

    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Авторизация по логину и паролю.
    """
    user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if (
        user is None
        or not verify_password(
            payload.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись отключена.",
        )

    if (
        user.role in SUBJECT_REQUIRED_ROLES
        and user.subject_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Для учётной записи не назначен предмет. "
                "Обратитесь к SUPER_ADMIN."
            ),
        )

    token = create_access_token(
        data={"sub": str(user.id)}
    )

    return TokenResponse(
        access_token=token,
        user=UserRead.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserRead,
)
def get_me(
    user: User = Depends(get_current_user),
):
    """
    Текущий авторизованный пользователь.
    """
    return UserRead.model_validate(user)