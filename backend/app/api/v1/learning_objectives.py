from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.learning_objective import LearningObjective
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.schemas.learning_objective import (
    LearningObjectiveCreate,
    LearningObjectiveList,
    LearningObjectiveRead,
    LearningObjectiveUpdate,
)


router = APIRouter(
    prefix="/learning-objectives"
)


require_objective_reader = RoleGuard(
    UserRole.SUPER_ADMIN,
    UserRole.CURATOR,
    UserRole.VERIFIER,
    UserRole.DEVELOPER,
)


require_objective_manager = RoleGuard(
    UserRole.SUPER_ADMIN,
    UserRole.CURATOR,
)


def get_subject_or_404(
    db: Session,
    subject_id: int,
) -> Subject:
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

    return subject


def get_objective_or_404(
    db: Session,
    objective_id: int,
) -> LearningObjective:
    objective = (
        db.query(LearningObjective)
        .filter(
            LearningObjective.id == objective_id
        )
        .first()
    )

    if objective is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ОРО не найден.",
        )

    return objective


def verify_objective_access(
    user: User,
    objective: LearningObjective,
) -> None:
    restricted_roles = {
        UserRole.DEVELOPER,
        UserRole.VERIFIER,
    }

    if user.role not in restricted_roles:
        return

    if user.subject_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Для учётной записи не назначен предмет. "
                "Обратитесь к SUPER_ADMIN."
            ),
        )

    if objective.subject_id != user.subject_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "У вас нет доступа к ОРО "
                "другого предмета."
            ),
        )


@router.get(
    "",
    response_model=LearningObjectiveList,
)
def list_learning_objectives(
    subject_id: int | None = Query(
        default=None,
        ge=1,
    ),
    include_inactive: bool = Query(
        default=False,
    ),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_objective_reader
    ),
):
    """
    Возвращает список ОРО.

    DEVELOPER и VERIFIER получают только ОРО
    назначенного им предмета.

    SUPER_ADMIN и CURATOR могут фильтровать
    список по subject_id.
    """
    query = db.query(LearningObjective)

    if user.role in {
        UserRole.DEVELOPER,
        UserRole.VERIFIER,
    }:
        if user.subject_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Для учётной записи не назначен "
                    "предмет. Обратитесь к SUPER_ADMIN."
                ),
            )

        query = query.filter(
            LearningObjective.subject_id
            == user.subject_id
        )

    elif subject_id is not None:
        query = query.filter(
            LearningObjective.subject_id
            == subject_id
        )

    if not include_inactive:
        query = query.filter(
            LearningObjective.is_active.is_(True)
        )

    items = (
        query
        .order_by(
            LearningObjective.subject_id.asc(),
            LearningObjective.code.asc(),
        )
        .all()
    )

    return LearningObjectiveList(
        items=items,
        total=len(items),
    )


@router.get(
    "/{objective_id}",
    response_model=LearningObjectiveRead,
)
def get_learning_objective(
    objective_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_objective_reader
    ),
):
    """
    Возвращает один ОРО с проверкой предмета.
    """
    objective = get_objective_or_404(
        db,
        objective_id,
    )

    verify_objective_access(
        user,
        objective,
    )

    return objective


@router.post(
    "",
    response_model=LearningObjectiveRead,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_objective(
    payload: LearningObjectiveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_objective_manager
    ),
):
    """
    Создаёт ОРО.

    Доступно только SUPER_ADMIN и CURATOR.
    """
    subject = get_subject_or_404(
        db,
        payload.subject_id,
    )

    if not subject.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Нельзя создать ОРО для "
                "неактивного предмета."
            ),
        )

    existing = (
        db.query(LearningObjective)
        .filter(
            LearningObjective.subject_id
            == payload.subject_id,
            LearningObjective.code
            == payload.code,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "ОРО с таким кодом уже существует "
                "для выбранного предмета."
            ),
        )

    objective = LearningObjective(
        subject_id=payload.subject_id,
        code=payload.code,
        title_kz=payload.title_kz,
        title_ru=payload.title_ru,
        is_active=True,
    )

    db.add(objective)
    db.commit()
    db.refresh(objective)

    return objective


@router.patch(
    "/{objective_id}",
    response_model=LearningObjectiveRead,
)
def update_learning_objective(
    objective_id: int,
    payload: LearningObjectiveUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_objective_manager
    ),
):
    """
    Изменяет код, названия или активность ОРО.

    Предмет ОРО после создания не меняется.
    """
    objective = get_objective_or_404(
        db,
        objective_id,
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
        duplicate = (
            db.query(LearningObjective)
            .filter(
                LearningObjective.subject_id
                == objective.subject_id,
                LearningObjective.code
                == update_data["code"],
                LearningObjective.id
                != objective.id,
            )
            .first()
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "ОРО с таким кодом уже существует "
                    "для выбранного предмета."
                ),
            )

        objective.code = update_data["code"]

    if "title_kz" in update_data:
        objective.title_kz = (
            update_data["title_kz"]
        )

    if "title_ru" in update_data:
        objective.title_ru = (
            update_data["title_ru"]
        )

    if "is_active" in update_data:
        objective.is_active = (
            update_data["is_active"]
        )

    db.commit()
    db.refresh(objective)

    return objective


@router.delete(
    "/{objective_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_learning_objective(
    objective_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_objective_manager
    ),
):
    """
    Деактивирует ОРО без физического удаления.

    Старые вопросы сохраняют ссылку на ОРО,
    но новый вопрос не сможет его выбрать.
    """
    objective = get_objective_or_404(
        db,
        objective_id,
    )

    if not objective.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ОРО уже деактивирован.",
        )

    objective.is_active = False

    db.commit()

    return None