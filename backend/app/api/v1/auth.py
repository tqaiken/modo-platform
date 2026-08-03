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
    UserLogin,
    UserRead,
)


router = APIRouter(prefix="/auth")


SUBJECT_REQUIRED_ROLES = {
    UserRole.DEVELOPER,
    UserRole.VERIFIER,
}


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

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Создание первого SUPER_ADMIN недоступно, "
                "поскольку пользователи уже существуют."
            ),
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.SUPER_ADMIN,
        subject_id=None,
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
    Создание пользователя.

    Доступно только SUPER_ADMIN.
    Для DEVELOPER и VERIFIER предмет обязателен.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Создавать пользователей может "
                "только SUPER_ADMIN."
            ),
        )

    existing_user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует.",
        )

    subject = None

    if payload.role in SUBJECT_REQUIRED_ROLES:
        if payload.subject_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Предмет обязателен для разработчика "
                    "и верификатора."
                ),
            )

        subject = (
            db.query(Subject)
            .filter(
                Subject.id == payload.subject_id,
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

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        subject_id=(
            subject.id
            if subject is not None
            else None
        ),
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


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Авторизация всех ролей по email и паролю.
    """
    user = (
        db.query(User)
        .filter(User.email == payload.email)
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
            detail="Неверный email или пароль.",
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