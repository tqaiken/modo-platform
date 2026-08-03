from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.question import Question
from app.models.user import User, UserRole
from app.models.variant import Variant, VariantStatus
from app.schemas.variant import (
    VariantCreate,
    VariantDashboard,
    VariantList,
    VariantRead,
    VariantUpdate,
)


router = APIRouter(prefix="/variants")


require_developer = RoleGuard(UserRole.DEVELOPER)


def serialize_variant(variant: Variant) -> VariantRead:
    """
    Convert a SQLAlchemy Variant object to the API response schema.
    """
    return VariantRead(
        id=variant.id,
        title=variant.title,
        description=variant.description,
        subject_id=variant.subject_id,
        developer_id=variant.developer_id,
        status=variant.status,
        question_count=len(variant.questions),
        created_at=variant.created_at,
        updated_at=variant.updated_at,
        submitted_at=variant.submitted_at,
        reviewed_at=variant.reviewed_at,
        approved_at=variant.approved_at,
    )


@router.post(
    "",
    response_model=VariantRead,
    status_code=status.HTTP_201_CREATED,
)
def create_variant(
    payload: VariantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """
    Создание нового варианта разработчиком.

    Предмет автоматически берётся из аккаунта разработчика.
    Разработчик не может выбрать или изменить предмет вручную.
    """
    if user.subject_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Для разработчика не назначен предмет. "
                "Обратитесь к SUPER_ADMIN."
            ),
        )

    variant = Variant(
        title=payload.title,
        description=payload.description,
        developer_id=user.id,
        subject_id=user.subject_id,
        status=VariantStatus.DRAFT,
    )

    db.add(variant)
    db.commit()
    db.refresh(variant)

    return serialize_variant(variant)


@router.get(
    "/my",
    response_model=VariantList,
)
def get_my_variants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    variant_status: VariantStatus | None = Query(
        default=None,
        alias="status",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """
    Return variants created by the current developer.
    """
    query = db.query(Variant).filter(
        Variant.developer_id == user.id
    )

    if variant_status is not None:
        query = query.filter(
            Variant.status == variant_status
        )

    total = query.count()

    variants = (
        query
        .order_by(Variant.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return VariantList(
        items=[
            serialize_variant(variant)
            for variant in variants
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/dashboard",
    response_model=VariantDashboard,
)
def get_developer_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """
    Return dashboard counters for the current developer.
    """
    base_query = db.query(Variant).filter(
        Variant.developer_id == user.id
    )

    total_variants = base_query.count()

    draft_variants = base_query.filter(
        Variant.status == VariantStatus.DRAFT
    ).count()

    verification_variants = base_query.filter(
        Variant.status == VariantStatus.VERIFICATION
    ).count()

    revision_variants = base_query.filter(
        Variant.status == VariantStatus.REVISION
    ).count()

    approved_variants = base_query.filter(
        Variant.status == VariantStatus.APPROVED
    ).count()

    bank_variants = base_query.filter(
        Variant.status == VariantStatus.IN_BANK
    ).count()

    total_questions = (
        db.query(func.count(Question.id))
        .join(
            Variant,
            Question.variant_id == Variant.id,
        )
        .filter(
            Variant.developer_id == user.id
        )
        .scalar()
        or 0
    )

    return VariantDashboard(
        total_variants=total_variants,
        draft_variants=draft_variants,
        verification_variants=verification_variants,
        revision_variants=revision_variants,
        approved_variants=approved_variants,
        bank_variants=bank_variants,
        total_questions=total_questions,
    )


@router.get(
    "/{variant_id}",
    response_model=VariantRead,
)
def get_variant(
    variant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """
    Return one variant belonging to the current developer.
    """
    variant = (
        db.query(Variant)
        .filter(
            Variant.id == variant_id,
            Variant.developer_id == user.id,
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found.",
        )

    return serialize_variant(variant)


@router.put(
    "/{variant_id}",
    response_model=VariantRead,
)
def update_variant(
    variant_id: int,
    payload: VariantUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """
    Update a draft or revision variant.
    """
    variant = (
        db.query(Variant)
        .filter(
            Variant.id == variant_id,
            Variant.developer_id == user.id,
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found.",
        )

    if variant.status not in (
        VariantStatus.DRAFT,
        VariantStatus.REVISION,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only DRAFT or REVISION variants "
                "can be edited."
            ),
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    for field_name, value in update_data.items():
        setattr(variant, field_name, value)

    db.commit()
    db.refresh(variant)

    return serialize_variant(variant)


@router.delete(
    "/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_variant(
    variant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """
    Delete a draft variant and all questions inside it.
    """
    variant = (
        db.query(Variant)
        .filter(
            Variant.id == variant_id,
            Variant.developer_id == user.id,
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found.",
        )

    if variant.status != VariantStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT variants can be deleted.",
        )

    db.delete(variant)
    db.commit()

    return None