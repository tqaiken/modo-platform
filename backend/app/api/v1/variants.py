from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.learning_objective import LearningObjective
from app.models.question import (
    Language,
    Question,
    QuestionStatus,
)
from app.models.user import User, UserRole
from app.models.variant import (
    Variant,
    VariantStatus,
)
from app.schemas.question import (
    VariantQuestionCreate,
    VariantQuestionList,
    VariantQuestionRead,
    VariantQuestionUpdate,
)
from app.schemas.variant import (
    VariantCreate,
    VariantDashboard,
    VariantList,
    VariantQueueItem,
    VariantQueueList,
    VariantRead,
    VariantReview,
    VariantReviewResult,
    VariantUpdate,
)


router = APIRouter(
    prefix="/variants",
)


require_developer = RoleGuard(
    UserRole.DEVELOPER,
)


require_verifier = RoleGuard(
    UserRole.VERIFIER,
)


EDITABLE_VARIANT_STATUSES = {
    VariantStatus.DRAFT,
    VariantStatus.REVISION,
}


def get_reviewer_name(
    variant: Variant,
) -> str | None:
    if variant.reviewer is None:
        return None

    return variant.reviewer.full_name


def serialize_variant(
    variant: Variant,
) -> VariantRead:
    return VariantRead(
        id=variant.id,
        title=variant.title,
        description=variant.description,
        subject_id=variant.subject_id,
        developer_id=variant.developer_id,
        reviewer_id=variant.reviewer_id,
        reviewer_name=get_reviewer_name(
            variant
        ),
        review_comment=variant.review_comment,
        status=variant.status,
        question_count=len(
            variant.questions
        ),
        created_at=variant.created_at,
        updated_at=variant.updated_at,
        submitted_at=variant.submitted_at,
        reviewed_at=variant.reviewed_at,
        approved_at=variant.approved_at,
    )


def serialize_queue_item(
    variant: Variant,
) -> VariantQueueItem:
    developer_name = (
        variant.developer.full_name
        if variant.developer is not None
        else f"Разработчик #{variant.developer_id}"
    )

    return VariantQueueItem(
        id=variant.id,
        title=variant.title,
        description=variant.description,
        subject_id=variant.subject_id,
        developer_id=variant.developer_id,
        developer_name=developer_name,
        status=variant.status,
        question_count=len(
            variant.questions
        ),
        created_at=variant.created_at,
        updated_at=variant.updated_at,
        submitted_at=variant.submitted_at,
        reviewed_at=variant.reviewed_at,
        approved_at=variant.approved_at,
    )


def serialize_question(
    question: Question,
) -> VariantQuestionRead:
    return VariantQuestionRead(
        id=question.id,
        variant_id=question.variant_id,
        order_number=question.order_number,
        learning_objective_id=(
            question.learning_objective_id
        ),
        cognitive_level=question.cognitive_level,
        resource_kz=question.resource_kz,
        resource_ru=question.resource_ru,
        question_text_kz=(
            question.question_text_kz
        ),
        question_text_ru=(
            question.question_text_ru
        ),
        options=question.options or [],
        explanation_kz=(
            question.explanation_kz
        ),
        explanation_ru=(
            question.explanation_ru
        ),
        subject_id=question.subject_id,
        status=question.status,
        author_id=question.author_id,
        reviewer_id=question.reviewer_id,
        media_files=question.media_files,
        comments=question.comments,
        created_at=question.created_at,
        updated_at=question.updated_at,
        submitted_at=question.submitted_at,
        reviewed_at=question.reviewed_at,
        approved_at=question.approved_at,
    )


def get_developer_variant_or_404(
    db: Session,
    variant_id: int,
    user: User,
) -> Variant:
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
            detail="Вариант не найден.",
        )

    return variant


def ensure_verifier_has_subject(
    user: User,
) -> int:
    if user.subject_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Для верификатора не назначен "
                "предмет. Обратитесь к "
                "супер-администратору."
            ),
        )

    return user.subject_id


def get_verification_variant_or_404(
    db: Session,
    variant_id: int,
    user: User,
) -> Variant:
    subject_id = ensure_verifier_has_subject(
        user
    )

    variant = (
        db.query(Variant)
        .filter(
            Variant.id == variant_id,
            Variant.subject_id == subject_id,
            Variant.status
            == VariantStatus.VERIFICATION,
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Вариант не найден в очереди "
                "верификации вашего предмета."
            ),
        )

    return variant


def ensure_variant_is_editable(
    variant: Variant,
) -> None:
    if (
        variant.status
        not in EDITABLE_VARIANT_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Вариант можно изменять только "
                "в статусе DRAFT или REVISION."
            ),
        )


def get_question_in_variant_or_404(
    db: Session,
    variant: Variant,
    question_id: int,
) -> Question:
    question = (
        db.query(Question)
        .filter(
            Question.id == question_id,
            Question.variant_id == variant.id,
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Вопрос не найден "
                "в указанном варианте."
            ),
        )

    return question


def get_valid_learning_objective(
    db: Session,
    learning_objective_id: int,
    subject_id: int,
) -> LearningObjective:
    objective = (
        db.query(LearningObjective)
        .filter(
            LearningObjective.id
            == learning_objective_id,
            LearningObjective.is_active.is_(
                True
            ),
        )
        .first()
    )

    if objective is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активный ОРО не найден.",
        )

    if objective.subject_id != subject_id:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Выбранный ОРО относится "
                "к другому предмету."
            ),
        )

    return objective


def get_next_order_number(
    db: Session,
    variant_id: int,
) -> int:
    current_max = (
        db.query(
            func.max(
                Question.order_number
            )
        )
        .filter(
            Question.variant_id == variant_id
        )
        .scalar()
    )

    return int(current_max or 0) + 1


def renumber_variant_questions(
    db: Session,
    variant_id: int,
) -> None:
    questions = (
        db.query(Question)
        .filter(
            Question.variant_id == variant_id
        )
        .order_by(
            Question.order_number.asc(),
            Question.id.asc(),
        )
        .all()
    )

    for index, question in enumerate(
        questions,
        start=1,
    ):
        question.order_number = index


def validate_question_for_submission(
    db: Session,
    question: Question,
    variant: Variant,
) -> None:
    question_number = (
        question.order_number
    )

    if (
        question.subject_id
        != variant.subject_id
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"Предмет вопроса №{question_number} "
                "не совпадает с предметом варианта."
            ),
        )

    if (
        question.learning_objective_id
        is None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"В вопросе №{question_number} "
                "не выбран ОРО."
            ),
        )

    objective = (
        db.query(LearningObjective)
        .filter(
            LearningObjective.id
            == question.learning_objective_id
        )
        .first()
    )

    if objective is None:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"ОРО вопроса №{question_number} "
                "не найден."
            ),
        )

    if not objective.is_active:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"ОРО вопроса №{question_number} "
                "деактивирован."
            ),
        )

    if (
        objective.subject_id
        != variant.subject_id
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"ОРО вопроса №{question_number} "
                "относится к другому предмету."
            ),
        )

    if question.cognitive_level is None:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"В вопросе №{question_number} "
                "не выбран когнитивный уровень."
            ),
        )

    if not str(
        question.question_text_kz or ""
    ).strip():
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"В вопросе №{question_number} "
                "не заполнен текст "
                "на казахском языке."
            ),
        )

    if not str(
        question.question_text_ru or ""
    ).strip():
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"В вопросе №{question_number} "
                "не заполнен текст "
                "на русском языке."
            ),
        )

    options = question.options or []

    if not isinstance(options, list):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"Варианты ответа вопроса "
                f"№{question_number} имеют "
                "некорректный формат."
            ),
        )

    if len(options) < 4:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"В вопросе №{question_number} "
                "должно быть минимум "
                "четыре ответа."
            ),
        )

    option_keys: list[str] = []
    correct_options_count = 0

    for option_index, option in enumerate(
        options,
        start=1,
    ):
        if not isinstance(option, dict):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"Ответ №{option_index} "
                    f"в вопросе №{question_number} "
                    "имеет некорректный формат."
                ),
            )

        option_key = str(
            option.get("key", "")
        ).strip()

        if not option_key:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"В вопросе №{question_number} "
                    "один из ответов "
                    "не имеет обозначения."
                ),
            )

        option_keys.append(option_key)

        text_kz = str(
            option.get("text_kz", "")
        ).strip()

        text_ru = str(
            option.get("text_ru", "")
        ).strip()

        if not text_kz or not text_ru:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"Ответ {option_key} "
                    f"в вопросе №{question_number} "
                    "не заполнен на двух языках."
                ),
            )

        if (
            option.get("is_correct")
            is True
        ):
            correct_options_count += 1

    if (
        len(option_keys)
        != len(set(option_keys))
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"В вопросе №{question_number} "
                "обозначения ответов повторяются."
            ),
        )

    if correct_options_count != 1:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                f"В вопросе №{question_number} "
                "должен быть выбран ровно "
                "один правильный ответ."
            ),
        )


# ============================================================
# Developer collection and dashboard
# ============================================================


@router.post(
    "",
    response_model=VariantRead,
    status_code=status.HTTP_201_CREATED,
)
def create_variant(
    payload: VariantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    if user.subject_id is None:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Для разработчика не назначен "
                "предмет. Обратитесь к "
                "супер-администратору."
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
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    variant_status: (
        VariantStatus | None
    ) = Query(
        default=None,
        alias="status",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    query = db.query(Variant).filter(
        Variant.developer_id == user.id
    )

    if variant_status is not None:
        query = query.filter(
            Variant.status
            == variant_status
        )

    total = query.count()

    variants = (
        query
        .order_by(
            Variant.updated_at.desc()
        )
        .offset(
            (page - 1) * page_size
        )
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
    user: User = Depends(
        require_developer
    ),
):
    base_query = (
        db.query(Variant)
        .filter(
            Variant.developer_id
            == user.id
        )
    )

    total_variants = (
        base_query.count()
    )

    draft_variants = (
        base_query
        .filter(
            Variant.status
            == VariantStatus.DRAFT
        )
        .count()
    )

    verification_variants = (
        base_query
        .filter(
            Variant.status
            == VariantStatus.VERIFICATION
        )
        .count()
    )

    revision_variants = (
        base_query
        .filter(
            Variant.status
            == VariantStatus.REVISION
        )
        .count()
    )

    approved_variants = (
        base_query
        .filter(
            Variant.status
            == VariantStatus.APPROVED
        )
        .count()
    )

    bank_variants = (
        base_query
        .filter(
            Variant.status
            == VariantStatus.IN_BANK
        )
        .count()
    )

    total_questions = (
        db.query(
            func.count(Question.id)
        )
        .join(
            Variant,
            Question.variant_id
            == Variant.id,
        )
        .filter(
            Variant.developer_id
            == user.id
        )
        .scalar()
        or 0
    )

    return VariantDashboard(
        total_variants=total_variants,
        draft_variants=draft_variants,
        verification_variants=(
            verification_variants
        ),
        revision_variants=(
            revision_variants
        ),
        approved_variants=(
            approved_variants
        ),
        bank_variants=bank_variants,
        total_questions=int(
            total_questions
        ),
    )


# ============================================================
# Verifier queue
# These static routes must precede /{variant_id}.
# ============================================================


@router.get(
    "/verification-queue",
    response_model=VariantQueueList,
)
def get_verification_queue(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_verifier
    ),
):
    subject_id = (
        ensure_verifier_has_subject(
            user
        )
    )

    query = (
        db.query(Variant)
        .filter(
            Variant.status
            == VariantStatus.VERIFICATION,
            Variant.subject_id
            == subject_id,
        )
    )

    total = query.count()

    variants = (
        query
        .order_by(
            Variant.submitted_at.asc(),
            Variant.id.asc(),
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
        .all()
    )

    return VariantQueueList(
        items=[
            serialize_queue_item(
                variant
            )
            for variant in variants
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================
# Developer submission
# ============================================================


@router.post(
    "/{variant_id}/submit",
    response_model=VariantRead,
)
def submit_variant_for_verification(
    variant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    ensure_variant_is_editable(
        variant
    )

    if variant.subject_id is None:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "У варианта не назначен предмет."
            ),
        )

    if user.subject_id is None:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Для разработчика не назначен "
                "предмет."
            ),
        )

    if (
        variant.subject_id
        != user.subject_id
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Предмет варианта не совпадает "
                "с предметом разработчика."
            ),
        )

    questions = (
        db.query(Question)
        .filter(
            Question.variant_id
            == variant.id
        )
        .order_by(
            Question.order_number.asc(),
            Question.id.asc(),
        )
        .all()
    )

    if not questions:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Нельзя отправить пустой вариант. "
                "Добавьте хотя бы один вопрос."
            ),
        )

    for question in questions:
        validate_question_for_submission(
            db,
            question,
            variant,
        )

    submitted_at = (
        datetime.now(timezone.utc)
    )

    variant.status = (
        VariantStatus.VERIFICATION
    )

    variant.submitted_at = (
        submitted_at
    )

    variant.reviewer_id = None
    variant.review_comment = None
    variant.reviewed_at = None
    variant.approved_at = None

    for question in questions:
        question.status = (
            QuestionStatus.VERIFICATION
        )

        question.submitted_at = (
            submitted_at
        )

        question.reviewer_id = None
        question.reviewed_at = None
        question.approved_at = None

    db.commit()
    db.refresh(variant)

    return serialize_variant(variant)


# ============================================================
# Verifier operations
# ============================================================


@router.get(
    "/{variant_id}/verification-questions",
    response_model=VariantQuestionList,
)
def get_verification_questions(
    variant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_verifier
    ),
):
    variant = (
        get_verification_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    questions = (
        db.query(Question)
        .filter(
            Question.variant_id
            == variant.id
        )
        .order_by(
            Question.order_number.asc(),
            Question.id.asc(),
        )
        .all()
    )

    if not questions:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "В отправленном варианте "
                "не найдены вопросы."
            ),
        )

    return VariantQuestionList(
        items=[
            serialize_question(
                question
            )
            for question in questions
        ],
        total=len(questions),
    )


@router.post(
    "/{variant_id}/review",
    response_model=VariantReviewResult,
)
def review_variant(
    variant_id: int,
    payload: VariantReview,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_verifier
    ),
):
    variant = (
        get_verification_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    questions = (
        db.query(Question)
        .filter(
            Question.variant_id
            == variant.id
        )
        .order_by(
            Question.order_number.asc(),
            Question.id.asc(),
        )
        .all()
    )

    if not questions:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Нельзя проверить пустой вариант."
            ),
        )

    reviewed_at = (
        datetime.now(timezone.utc)
    )

    variant.reviewer_id = user.id
    variant.review_comment = (
        payload.comment
    )

    variant.reviewed_at = reviewed_at

    if payload.approved:
        variant.status = (
            VariantStatus.APPROVED
        )

        variant.approved_at = (
            reviewed_at
        )

        for question in questions:
            question.status = (
                QuestionStatus.IN_BANK
            )

            question.reviewer_id = (
                user.id
            )

            question.reviewed_at = (
                reviewed_at
            )

            question.approved_at = (
                reviewed_at
            )
    else:
        variant.status = (
            VariantStatus.REVISION
        )

        variant.approved_at = None

        for question in questions:
            question.status = (
                QuestionStatus.REVISION
            )

            question.reviewer_id = (
                user.id
            )

            question.reviewed_at = (
                reviewed_at
            )

            question.approved_at = None

    db.commit()
    db.refresh(variant)

    return VariantReviewResult(
        id=variant.id,
        title=variant.title,
        status=variant.status,
        reviewer_id=variant.reviewer_id,
        reviewer_name=(
            get_reviewer_name(
                variant
            )
        ),
        review_comment=(
            variant.review_comment
        ),
        question_count=len(
            variant.questions
        ),
        submitted_at=(
            variant.submitted_at
        ),
        reviewed_at=(
            variant.reviewed_at
        ),
        approved_at=(
            variant.approved_at
        ),
    )


# ============================================================
# Developer nested questions
# ============================================================


@router.get(
    "/{variant_id}/questions",
    response_model=VariantQuestionList,
)
def get_variant_questions(
    variant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    questions = (
        db.query(Question)
        .filter(
            Question.variant_id
            == variant.id
        )
        .order_by(
            Question.order_number.asc(),
            Question.id.asc(),
        )
        .all()
    )

    return VariantQuestionList(
        items=[
            serialize_question(
                question
            )
            for question in questions
        ],
        total=len(questions),
    )


@router.post(
    "/{variant_id}/questions",
    response_model=VariantQuestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_question_in_variant(
    variant_id: int,
    payload: VariantQuestionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    ensure_variant_is_editable(
        variant
    )

    if variant.subject_id is None:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "У варианта не назначен предмет."
            ),
        )

    if (
        user.subject_id is None
        or variant.subject_id
        != user.subject_id
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Предмет варианта не совпадает "
                "с предметом разработчика."
            ),
        )

    objective = (
        get_valid_learning_objective(
            db,
            payload.learning_objective_id,
            variant.subject_id,
        )
    )

    order_number = (
        get_next_order_number(
            db,
            variant.id,
        )
    )

    serialized_options = [
        option.model_dump()
        for option in payload.options
    ]

    question = Question(
        variant_id=variant.id,
        order_number=order_number,
        learning_objective_id=(
            objective.id
        ),
        cognitive_level=(
            payload.cognitive_level
        ),
        resource_kz=payload.resource_kz,
        resource_ru=payload.resource_ru,
        question_text_kz=(
            payload.question_text_kz
        ),
        question_text_ru=(
            payload.question_text_ru
        ),
        options=serialized_options,
        explanation_kz=(
            payload.explanation_kz
        ),
        explanation_ru=(
            payload.explanation_ru
        ),
        subject_id=variant.subject_id,
        author_id=user.id,
        reviewer_id=None,
        status=QuestionStatus.DRAFT,
        title=f"Вопрос {order_number}",
        body=(
            payload.question_text_ru
        ),
        explanation=(
            payload.explanation_ru
        ),
        language=Language.RU,
        subject=(
            variant.subject.title
            if variant.subject is not None
            else None
        ),
        topic=objective.code,
        difficulty={
            "BASIC": 1,
            "MEDIUM": 3,
            "HIGH": 5,
        }[
            payload
            .cognitive_level
            .value
        ],
    )

    db.add(question)

    variant.updated_at = func.now()

    db.commit()
    db.refresh(question)

    return serialize_question(
        question
    )


@router.patch(
    "/{variant_id}/questions/{question_id}",
    response_model=VariantQuestionRead,
)
def update_question_in_variant(
    variant_id: int,
    question_id: int,
    payload: VariantQuestionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    ensure_variant_is_editable(
        variant
    )

    question = (
        get_question_in_variant_or_404(
            db,
            variant,
            question_id,
        )
    )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Не переданы данные "
                "для изменения."
            ),
        )

    if (
        "learning_objective_id"
        in update_data
    ):
        if variant.subject_id is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "У варианта не назначен "
                    "предмет."
                ),
            )

        objective = (
            get_valid_learning_objective(
                db,
                update_data[
                    "learning_objective_id"
                ],
                variant.subject_id,
            )
        )

        question.learning_objective_id = (
            objective.id
        )

        question.topic = objective.code

    if (
        "cognitive_level"
        in update_data
    ):
        cognitive_level = (
            update_data[
                "cognitive_level"
            ]
        )

        question.cognitive_level = (
            cognitive_level
        )

        question.difficulty = {
            "BASIC": 1,
            "MEDIUM": 3,
            "HIGH": 5,
        }[
            cognitive_level.value
        ]

    if "resource_kz" in update_data:
        question.resource_kz = (
            update_data["resource_kz"]
        )

    if "resource_ru" in update_data:
        question.resource_ru = (
            update_data["resource_ru"]
        )

    if (
        "question_text_kz"
        in update_data
    ):
        question.question_text_kz = (
            update_data[
                "question_text_kz"
            ]
        )

    if (
        "question_text_ru"
        in update_data
    ):
        question.question_text_ru = (
            update_data[
                "question_text_ru"
            ]
        )

        question.body = (
            update_data[
                "question_text_ru"
            ]
        )

    if "options" in update_data:
        question.options = [
            (
                option.model_dump()
                if hasattr(
                    option,
                    "model_dump",
                )
                else option
            )
            for option in (
                update_data["options"]
            )
        ]

    if (
        "explanation_kz"
        in update_data
    ):
        question.explanation_kz = (
            update_data[
                "explanation_kz"
            ]
        )

    if (
        "explanation_ru"
        in update_data
    ):
        question.explanation_ru = (
            update_data[
                "explanation_ru"
            ]
        )

        question.explanation = (
            update_data[
                "explanation_ru"
            ]
        )

    variant.updated_at = func.now()

    db.commit()
    db.refresh(question)

    return serialize_question(
        question
    )


@router.delete(
    "/{variant_id}/questions/{question_id}",
    status_code=(
        status.HTTP_204_NO_CONTENT
    ),
)
def delete_question_from_variant(
    variant_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    ensure_variant_is_editable(
        variant
    )

    question = (
        get_question_in_variant_or_404(
            db,
            variant,
            question_id,
        )
    )

    db.delete(question)
    db.flush()

    renumber_variant_questions(
        db,
        variant.id,
    )

    variant.updated_at = func.now()

    db.commit()

    return None


# ============================================================
# Individual developer variant
# ============================================================


@router.get(
    "/{variant_id}",
    response_model=VariantRead,
)
def get_variant(
    variant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
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
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    ensure_variant_is_editable(
        variant
    )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Не переданы данные "
                "для изменения."
            ),
        )

    for field_name, value in (
        update_data.items()
    ):
        setattr(
            variant,
            field_name,
            value,
        )

    db.commit()
    db.refresh(variant)

    return serialize_variant(variant)


@router.delete(
    "/{variant_id}",
    status_code=(
        status.HTTP_204_NO_CONTENT
    ),
)
def delete_variant(
    variant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    variant = (
        get_developer_variant_or_404(
            db,
            variant_id,
            user,
        )
    )

    if (
        variant.status
        != VariantStatus.DRAFT
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Удалить можно только вариант "
                "со статусом DRAFT."
            ),
        )

    db.delete(variant)
    db.commit()

    return None