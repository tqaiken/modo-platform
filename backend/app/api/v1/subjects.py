"""CRUD API for the subjects reference table."""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.subject import Subject
from app.models.user import User, UserRole


router = APIRouter(prefix="/subjects")


# Все рабочие роли могут получить список предметов.
require_subject_reader = RoleGuard(
    UserRole.SUPER_ADMIN,
    UserRole.CURATOR,
    UserRole.VERIFIER,
    UserRole.DEVELOPER,
)

# Управлять справочником могут SUPER_ADMIN и CURATOR.
require_subject_manager = RoleGuard(
    UserRole.SUPER_ADMIN,
    UserRole.CURATOR,
)


class SubjectCreate(BaseModel):
    code: str = Field(
        min_length=2,
        max_length=50,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    title_kz: str | None = Field(
        default=None,
        max_length=255,
    )


class SubjectUpdate(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    title_kz: str | None = Field(
        default=None,
        max_length=255,
    )

    is_active: bool | None = None


class SubjectRead(BaseModel):
    id: int
    code: str
    title: str
    title_kz: str | None = None
    is_active: bool

    model_config = {
        "from_attributes": True,
    }


@router.get(
    "",
    response_model=list[SubjectRead],
)
def list_subjects(
    db: Session = Depends(get_db),
    user: User = Depends(require_subject_reader),
):
    """
    Возвращает список всех активных предметов.

    Доступно:
    - SUPER_ADMIN;
    - CURATOR;
    - VERIFIER;
    - DEVELOPER.
    """
    return (
        db.query(Subject)
        .filter(Subject.is_active.is_(True))
        .order_by(Subject.title.asc())
        .all()
    )


@router.post(
    "",
    response_model=SubjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_subject_manager),
):
    """
    Создаёт предмет.

    Доступно только SUPER_ADMIN и CURATOR.
    """
    normalized_code = payload.code.strip().lower()

    existing = (
        db.query(Subject)
        .filter(Subject.code == normalized_code)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Предмет с кодом "
                f"'{normalized_code}' уже существует."
            ),
        )

    subject = Subject(
        code=normalized_code,
        title=payload.title.strip(),
        title_kz=(
            payload.title_kz.strip()
            if payload.title_kz
            else None
        ),
        is_active=True,
    )

    db.add(subject)
    db.commit()
    db.refresh(subject)

    return subject


@router.put(
    "/{subject_id}",
    response_model=SubjectRead,
)
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_subject_manager),
):
    """
    Изменяет существующий предмет.

    Доступно только SUPER_ADMIN и CURATOR.
    """
    subject = (
        db.query(Subject)
        .filter(Subject.id == subject_id)
        .first()
    )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предмет не найден.",
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не переданы данные для изменения.",
        )

    if "code" in update_data:
        normalized_code = update_data["code"].strip().lower()

        duplicate = (
            db.query(Subject)
            .filter(
                Subject.code == normalized_code,
                Subject.id != subject_id,
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Предмет с кодом "
                    f"'{normalized_code}' уже существует."
                ),
            )

        subject.code = normalized_code

    if "title" in update_data:
        subject.title = update_data["title"].strip()

    if "title_kz" in update_data:
        subject.title_kz = (
            update_data["title_kz"].strip()
            if update_data["title_kz"]
            else None
        )

    if "is_active" in update_data:
        subject.is_active = update_data["is_active"]

    db.commit()
    db.refresh(subject)

    return subject


@router.delete(
    "/{subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_subject_manager),
):
    """
    Деактивирует предмет без физического удаления.

    Доступно только SUPER_ADMIN и CURATOR.
    """
    subject = (
        db.query(Subject)
        .filter(Subject.id == subject_id)
        .first()
    )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предмет не найден.",
        )

    if not subject.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Предмет уже деактивирован.",
        )

    subject.is_active = False

    db.commit()

    return None