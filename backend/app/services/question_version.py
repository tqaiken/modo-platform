from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.question import Question
from app.models.question_version import (
    QuestionVersion,
)


def _enum_value(
    value: Any,
) -> Any:
    """
    Возвращает JSON-совместимое значение Enum.
    """
    if value is None:
        return None

    return getattr(
        value,
        "value",
        value,
    )


def build_question_snapshot(
    question: Question,
) -> dict[str, Any]:
    """
    Формирует полный JSON-снимок вопроса.

    Снимок содержит новые двуязычные поля,
    legacy-поля и метаданные связанных медиа.
    """
    media_files = []

    for media in (
        question.media_files
        or []
    ):
        media_files.append(
            {
                "id": getattr(
                    media,
                    "id",
                    None,
                ),
                "r2_key": getattr(
                    media,
                    "r2_key",
                    None,
                ),
                "original_filename": getattr(
                    media,
                    "original_filename",
                    None,
                ),
                "content_type": getattr(
                    media,
                    "content_type",
                    None,
                ),
                "file_size": getattr(
                    media,
                    "file_size",
                    None,
                ),
            }
        )

    return {
        "variant_id": (
            question.variant_id
        ),
        "order_number": (
            question.order_number
        ),
        "learning_objective_id": (
            question.learning_objective_id
        ),
        "cognitive_level": _enum_value(
            question.cognitive_level
        ),
        "resource_kz": (
            question.resource_kz
        ),
        "resource_ru": (
            question.resource_ru
        ),
        "question_text_kz": (
            question.question_text_kz
        ),
        "question_text_ru": (
            question.question_text_ru
        ),
        "options": list(
            question.options
            or []
        ),
        "explanation_kz": (
            question.explanation_kz
        ),
        "explanation_ru": (
            question.explanation_ru
        ),
        "subject_id": (
            question.subject_id
        ),
        "status": _enum_value(
            question.status
        ),
        "author_id": (
            question.author_id
        ),
        "reviewer_id": (
            question.reviewer_id
        ),
        "submitted_at": (
            question.submitted_at.isoformat()
            if question.submitted_at
            else None
        ),
        "reviewed_at": (
            question.reviewed_at.isoformat()
            if question.reviewed_at
            else None
        ),
        "approved_at": (
            question.approved_at.isoformat()
            if question.approved_at
            else None
        ),
        "media_files": media_files,
        "legacy": {
            "title": question.title,
            "body": question.body,
            "body_html": (
                question.body_html
            ),
            "explanation": (
                question.explanation
            ),
            "language": _enum_value(
                question.language
            ),
            "subject": (
                question.subject
            ),
            "topic": (
                question.topic
            ),
            "difficulty": (
                question.difficulty
            ),
        },
    }


def create_question_version(
    db: Session,
    question: Question,
    created_by_id: int,
    change_reason: str,
    change_details: str | None = None,
) -> QuestionVersion:
    """
    Создаёт следующую неизменяемую версию вопроса.

    Функция выполняет flush, но не commit. Транзакцией
    управляет вызывающий API endpoint.
    """
    if question.id is None:
        db.flush()

    current_max = (
        db.query(
            func.max(
                QuestionVersion.version_number
            )
        )
        .filter(
            QuestionVersion.question_id
            == question.id
        )
        .scalar()
    )

    next_version_number = int(
        current_max
        or 0
    ) + 1

    version = QuestionVersion(
        question_id=question.id,
        version_number=(
            next_version_number
        ),
        snapshot=build_question_snapshot(
            question
        ),
        change_reason=change_reason,
        change_details=change_details,
        created_by_id=created_by_id,
    )

    db.add(version)
    db.flush()

    return version