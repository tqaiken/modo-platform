from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.security import get_current_user, RoleGuard
from app.models.user import User, UserRole
from app.models.question import (
    Question,
    QuestionStatus,
)
from app.models.question_version import (
    QuestionVersion,
)
from app.models.log import LogAction
from app.models.comment import ReviewComment
from app.schemas.question import (
    QuestionCreate,
    QuestionList,
    QuestionRead,
    QuestionReview,
    QuestionSubmit,
    QuestionUpdate,
    QuestionVersionList,
    QuestionVersionRead,
)
from app.services.audit import log_action
from app.services.question_version import (
    create_question_version,
)

router = APIRouter(prefix="/questions")

# ── Role dependencies ──
require_developer = RoleGuard(UserRole.DEVELOPER)
require_verifier = RoleGuard(UserRole.VERIFIER)
require_curator = RoleGuard(UserRole.CURATOR)
require_any = RoleGuard(UserRole.DEVELOPER, UserRole.VERIFIER, UserRole.CURATOR, UserRole.SUPER_ADMIN)

def get_visible_question_or_404(
    db: Session,
    question_id: int,
    user: User,
) -> Question:
    """
    Возвращает вопрос, если текущий пользователь
    имеет право просматривать его историю.
    """
    question = (
        db.query(Question)
        .filter(
            Question.id == question_id
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    if (
        user.role
        == UserRole.SUPER_ADMIN
    ):
        return question

    if user.role == UserRole.CURATOR:
        return question

    if user.role == UserRole.DEVELOPER:
        if question.author_id != user.id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Нет доступа к истории "
                    "этого вопроса."
                ),
            )

        return question

    if user.role == UserRole.VERIFIER:
        if (
            user.subject_id is None
            or question.subject_id
            != user.subject_id
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Нет доступа к истории "
                    "вопроса другого предмета."
                ),
            )

        return question

    raise HTTPException(
        status_code=403,
        detail="Access denied",
    )

# ──────────────────── DEVELOPER ────────────────────


@router.post("", response_model=QuestionRead, status_code=201)
def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """Create a new question (DRAFT)."""
    q = Question(
        title=payload.title,
        body=payload.body,
        options=[opt.model_dump() for opt in payload.options],
        explanation=payload.explanation,
        language=payload.language,
        subject_id=payload.subject_id,
        subject=payload.subject,
        topic=payload.topic,
        difficulty=payload.difficulty,
        author_id=user.id,
        status=QuestionStatus.DRAFT,
    )
    db.add(q)
    db.flush()

    create_question_version(
        db=db,
        question=q,
        created_by_id=user.id,
        change_reason="CREATED",
        change_details=(
            "Создан первоначальный снимок вопроса."
        ),
    )

    log_action(
        db,
        q.id,
        user.id,
        LogAction.CREATED,
        f"Question created: {q.title}",
    )

    db.commit()
    db.refresh(q)
    return q


@router.put("/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """Update a DRAFT or REVISION question."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    if q.author_id != user.id:
        raise HTTPException(403, "Not your question")
    if q.status not in (QuestionStatus.DRAFT, QuestionStatus.REVISION):
        raise HTTPException(400, f"Cannot edit question with status '{q.status.value}'")

    update_data = payload.model_dump(exclude_unset=True)
    if "options" in update_data and update_data["options"] is not None:
        update_data["options"] = [
            opt.model_dump() if hasattr(opt, "model_dump") else opt
            for opt in update_data["options"]
        ]
    for field, value in update_data.items():
        setattr(q, field, value)

    changed_fields = sorted(
        update_data.keys()
    )

    create_question_version(
        db=db,
        question=q,
        created_by_id=user.id,
        change_reason="UPDATED",
        change_details=(
            "Изменены поля: "
            + ", ".join(changed_fields)
        ),
    )

    log_action(
        db,
        q.id,
        user.id,
        LogAction.UPDATED,
        (
            "Fields updated: "
            f"{changed_fields}"
        ),
    )

    db.commit()
    db.refresh(q)
    return q


@router.post("/{question_id}/submit", response_model=QuestionRead)
def submit_for_verification(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """Submit question for verification (DRAFT/REVISION → VERIFICATION)."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    if q.author_id != user.id:
        raise HTTPException(403, "Not your question")
    if q.status not in (QuestionStatus.DRAFT, QuestionStatus.REVISION):
        raise HTTPException(400, f"Cannot submit question with status '{q.status.value}'")

    previous_status = q.status

    q.status = QuestionStatus.VERIFICATION
    q.submitted_at = datetime.now(
        timezone.utc
    )

    create_question_version(
        db=db,
        question=q,
        created_by_id=user.id,
        change_reason="SUBMITTED",
        change_details=(
            "Статус изменён: "
            f"{previous_status.value} -> "
            f"{q.status.value}."
        ),
    )

    log_action(
        db,
        q.id,
        user.id,
        LogAction.SUBMITTED,
        "Submitted for verification",
    )

    db.commit()
    db.refresh(q)
    return q


@router.delete("/{question_id}", status_code=204)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """Delete a DRAFT question."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    if q.author_id != user.id:
        raise HTTPException(403, "Not your question")
    if q.status != QuestionStatus.DRAFT:
        raise HTTPException(400, "Can only delete DRAFT questions")

    db.delete(q)
    db.commit()


# ──────────────────── VERIFIER ────────────────────


@router.get(
    "/verification-queue",
    response_model=QuestionList,
)
def get_verification_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(RoleGuard(UserRole.VERIFIER, UserRole.SUPER_ADMIN)),
):
    query = db.query(Question).filter(
        Question.status == QuestionStatus.VERIFICATION,
    )

    if user.role != UserRole.SUPER_ADMIN:
        if user.subject_id is None:
            raise HTTPException(
                status_code=403,
                detail="Для верификатора не назначен предмет. Обратитесь к SUPER_ADMIN.",
            )
        query = query.filter(Question.subject_id == user.subject_id)

    total = query.count()
    items = (
        query
        .order_by(Question.submitted_at.asc(), Question.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return QuestionList(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/{question_id}/review",
    response_model=QuestionRead,
)
def review_question(
    question_id: int,
    payload: QuestionReview,
    db: Session = Depends(get_db),
    user: User = Depends(RoleGuard(UserRole.VERIFIER, UserRole.SUPER_ADMIN)),
):
    """
    Проверяет вопрос по предмету текущего верификатора.

    approved=True:
        VERIFICATION → IN_BANK

    approved=False:
        VERIFICATION → REVISION

    Верификатор может внести разрешённые правки
    и обязательно сохранить комментарий проверки.
    """
    if user.subject_id is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Для верификатора не назначен предмет. "
                "Обратитесь к SUPER_ADMIN."
            ),
        )

    q = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if q is None:
        raise HTTPException(
            status_code=404,
            detail="Вопрос не найден.",
        )

    if user.role != UserRole.SUPER_ADMIN:
        if user.subject_id is None:
            raise HTTPException(
                status_code=403,
                detail="Для верификатора не назначен предмет. Обратитесь к SUPER_ADMIN.",
            )
        if q.subject_id != user.subject_id:
            raise HTTPException(
                status_code=403,
                detail="Вы не можете проверять вопросы по другому предмету.",
            )

    if q.status != QuestionStatus.VERIFICATION:
        raise HTTPException(
            status_code=400,
            detail=(
                "Вопрос не находится на верификации. "
                f"Текущий статус: {q.status.value}."
            ),
        )

    # Сохраняем предыдущий статус для полной хронологии.
    previous_status = q.status

    # Разрешённые правки верификатора.
    edits_applied: list[str] = []

    if (
        payload.edited_title is not None
        and payload.edited_title != q.title
    ):
        q.title = payload.edited_title
        edits_applied.append("title")

    if (
        payload.edited_body is not None
        and payload.edited_body != q.body
    ):
        q.body = payload.edited_body
        edits_applied.append("body")

    if payload.edited_options is not None:
        new_options = [
            option.model_dump()
            for option in payload.edited_options
        ]

        if new_options != q.options:
            q.options = new_options
            edits_applied.append("options")

    if (
        payload.edited_explanation is not None
        and payload.edited_explanation != q.explanation
    ):
        q.explanation = payload.edited_explanation
        edits_applied.append("explanation")

    if edits_applied:
        log_action(
            db,
            q.id,
            user.id,
            LogAction.EDITED_BY_VERIFIER,
            (
                "Верификатор изменил поля: "
                f"{', '.join(edits_applied)}"
            ),
        )

    # Комментарий проверки.
    comment_text = payload.comment.strip()

    if not comment_text:
        raise HTTPException(
            status_code=422,
            detail="Комментарий верификатора обязателен.",
        )

    comment = ReviewComment(
        question_id=q.id,
        author_id=user.id,
        content=comment_text,
    )

    db.add(comment)

    now = datetime.now(timezone.utc)

    q.reviewer_id = user.id
    q.reviewed_at = now

    if payload.approved:
        q.status = QuestionStatus.IN_BANK
        q.approved_at = now
        create_question_version(
            db=db,
            question=q,
            created_by_id=user.id,
            change_reason="APPROVED",
            change_details=(
                "Вопрос утверждён верификатором. "
                "Статус изменён: "
                f"{previous_status.value} -> "
                f"{q.status.value}. "
                f"Комментарий: {comment_text}"
            ),
        )
        log_action(
            db,
            q.id,
            user.id,
            LogAction.APPROVED,
            (
                f"Статус изменён: "
                f"{previous_status.value} → {q.status.value}. "
                f"Комментарий: {comment_text}"
            ),
        )
    else:
        q.status = QuestionStatus.REVISION
        q.approved_at = None
        create_question_version(
            db=db,
            question=q,
            created_by_id=user.id,
            change_reason="RETURNED",
            change_details=(
                "Вопрос возвращён на доработку. "
                "Статус изменён: "
                f"{previous_status.value} -> "
                f"{q.status.value}. "
                f"Комментарий: {comment_text}"
            ),
        )
        log_action(
            db,
            q.id,
            user.id,
            LogAction.REJECTED,
            (
                f"Статус изменён: "
                f"{previous_status.value} → {q.status.value}. "
                f"Комментарий: {comment_text}"
            ),
        )

    db.commit()
    db.refresh(q)

    return q


# ──────────────────── CURATOR / SHARED ────────────────────


@router.get("/bank", response_model=QuestionList)
def get_question_bank(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    subject: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    """Browse the approved question bank."""
    query = db.query(Question).filter(Question.status == QuestionStatus.IN_BANK)

    if subject:
        query = query.filter(Question.subject == subject)
    if topic:
        query = query.filter(Question.topic == topic)
    if language:
        query = query.filter(Question.language == language)
    if search:
        query = query.filter(
            or_(
                Question.title.ilike(f"%{search}%"),
                Question.body.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    items = (
        query.order_by(Question.approved_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return QuestionList(items=items, total=total, page=page, page_size=page_size)


@router.get("/my", response_model=QuestionList)
def get_my_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: QuestionStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """List developer's own questions."""
    query = db.query(Question).filter(Question.author_id == user.id)
    if status:
        query = query.filter(Question.status == status)

    total = query.count()
    items = (
        query.order_by(Question.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return QuestionList(items=items, total=total, page=page, page_size=page_size)

@router.get(
    "/{question_id}/versions",
    response_model=QuestionVersionList,
)
def get_question_versions(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    """
    Возвращает историю версий вопроса.

    Новейшие версии отображаются первыми.
    """
    question = (
        get_visible_question_or_404(
            db,
            question_id,
            user,
        )
    )

    versions = (
        db.query(QuestionVersion)
        .filter(
            QuestionVersion.question_id
            == question.id
        )
        .order_by(
            QuestionVersion
            .version_number
            .desc()
        )
        .all()
    )

    return QuestionVersionList(
        items=versions,
        total=len(versions),
    )


@router.get(
    "/{question_id}/versions/{version_number}",
    response_model=QuestionVersionRead,
)
def get_question_version(
    question_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    """
    Возвращает конкретную версию вопроса.
    """
    if version_number < 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "Номер версии должен быть "
                "не меньше 1."
            ),
        )

    question = (
        get_visible_question_or_404(
            db,
            question_id,
            user,
        )
    )

    version = (
        db.query(QuestionVersion)
        .filter(
            QuestionVersion.question_id
            == question.id,
            QuestionVersion.version_number
            == version_number,
        )
        .first()
    )

    if version is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Версия вопроса не найдена."
            ),
        )

    return version

@router.get("/{question_id}", response_model=QuestionRead)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    """Get a single question by ID."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    return q
