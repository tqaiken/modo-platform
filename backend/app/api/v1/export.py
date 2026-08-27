"""
Export API.

Endpoints:

POST /export/zip
    Legacy ZIP export of individual questions.

POST /export/variants/zip
    ZIP export of complete variants from the bank.
"""

import io
import json
import logging
import re
import zipfile
from datetime import (
    date,
    datetime,
    timezone,
)
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy.orm import (
    Session,
    joinedload,
    selectinload,
)

from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.question import (
    Question,
    QuestionStatus,
)
from app.models.user import User, UserRole
from app.models.variant import (
    Variant,
    VariantStatus,
)
from app.services.export_pdf import (
    generate_test_bank_pdf,
    generate_variants_test_bank_pdf,
)
from app.services.export_xlsx import (
    generate_registry_xlsx,
    generate_variants_registry_xlsx,
)
from app.services.latex_validator import (
    validate_question_latex,
)
from app.services.r2 import (
    create_s3_client,
    get_r2_bucket_name,
    normalize_r2_key,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/export",
)


require_legacy_export = RoleGuard(
    UserRole.CURATOR,
    UserRole.VERIFIER,
)


require_curator = RoleGuard(
    UserRole.CURATOR,
)


class ExportRequest(BaseModel):
    """
    Legacy request for exporting
    individual questions.
    """

    question_ids: list[int] = Field(
        min_length=1,
        max_length=1000,
    )


class VariantExportRequest(BaseModel):
    """
    Request for exporting complete variants.
    """

    variant_ids: list[int] = Field(
        min_length=1,
        max_length=100,
    )


def normalize_ids(
    values: list[int],
) -> list:
    """
    Удаляет повторяющиеся идентификаторы,
    сохраняя их исходный порядок.
    """
    result: list[int] = []
    seen: set[int] = set()

    for value in values:
        normalized_value = int(value)

        if normalized_value < 1:
            continue

        if normalized_value in seen:
            continue

        seen.add(normalized_value)
        result.append(normalized_value)

    return result


def safe_archive_name(
    value: str | None,
    fallback: str,
) -> str:
    """
    Creates a safe filename for a ZIP archive.
    """
    filename = Path(
        str(value or fallback)
    ).name.strip()

    filename = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "_",
        filename,
    )

    filename = re.sub(
        r"\s+",
        " ",
        filename,
    ).strip(" .")

    if not filename:
        return fallback

    return filename[:180]


def json_default(
    value: Any,
) -> Any:
    """
    Converts values unsupported by json.dumps.
    """
    if isinstance(
        value,
        (
            datetime,
            date,
        ),
    ):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    return str(value)


def write_json(
    archive: zipfile.ZipFile,
    archive_path: str,
    payload: Any,
) -> None:
    """
    Writes UTF-8 JSON into the ZIP archive.
    """
    content = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=json_default,
    ).encode("utf-8")

    archive.writestr(
        archive_path,
        content,
    )


def get_user_name(
    user: Any,
) -> str | None:
    """
    Returns the display name of a user.
    """
    if user is None:
        return None

    full_name = getattr(
        user,
        "full_name",
        None,
    )

    if full_name:
        return str(full_name)

    username = getattr(
        user,
        "username",
        None,
    )

    if username:
        return str(username)

    return None


def serialize_media(
    media: Any,
) -> dict[str, Any]:
    """
    Serializes media metadata for JSON export.
    """
    return {
        "id": media.id,
        "original_filename": (
            media.original_filename
        ),
        "r2_key": media.r2_key,
        "content_type": media.content_type,
        "file_size": media.file_size,
        "width": media.width,
        "height": media.height,
        "uploaded_at": media.uploaded_at,
    }


def serialize_question(
    question: Question,
) -> dict[str, Any]:
    """
    Serializes a bilingual variant question.
    """
    media_files = sorted(
        question.media_files,
        key=lambda media: media.id,
    )

    return {
        "id": question.id,
        "variant_id": question.variant_id,
        "order_number": (
            question.order_number
        ),
        "learning_objective_id": (
            question.learning_objective_id
        ),
        "cognitive_level": (
            question.cognitive_level
        ),
        "resource_kz": question.resource_kz,
        "resource_ru": question.resource_ru,
        "question_text_kz": (
            question.question_text_kz
        ),
        "question_text_ru": (
            question.question_text_ru
        ),
        "options": question.options or [],
        "explanation_kz": (
            question.explanation_kz
        ),
        "explanation_ru": (
            question.explanation_ru
        ),
        "subject_id": question.subject_id,
        "status": question.status,
        "author_id": question.author_id,
        "reviewer_id": question.reviewer_id,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "submitted_at": question.submitted_at,
        "reviewed_at": question.reviewed_at,
        "approved_at": question.approved_at,
        "media_files": [
            serialize_media(media)
            for media in media_files
        ],
    }


def serialize_variant(
    variant: Variant,
) -> dict[str, Any]:
    """
    Serializes a complete variant.
    """
    questions = sorted(
        variant.questions,
        key=lambda question: (
            question.order_number or 0,
            question.id,
        ),
    )

    subject_data: dict[str, Any] = {
        "id": variant.subject_id,
        "code": None,
        "title": None,
        "title_kz": None,
    }

    if variant.subject is not None:
        subject_data = {
            "id": variant.subject.id,
            "code": variant.subject.code,
            "title": variant.subject.title,
            "title_kz": (
                variant.subject.title_kz
            ),
        }

    return {
        "id": variant.id,
        "title": variant.title,
        "description": variant.description,
        "subject": subject_data,
        "developer": {
            "id": variant.developer_id,
            "name": get_user_name(
                variant.developer
            ),
        },
        "verifier": {
            "id": variant.reviewer_id,
            "name": get_user_name(
                variant.reviewer
            ),
            "comment": (
                variant.review_comment
            ),
        },
        "curator": {
            "id": variant.curator_id,
            "name": get_user_name(
                variant.curator
            ),
            "comment": (
                variant.curator_comment
            ),
        },
        "status": variant.status,
        "question_count": len(questions),
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
        "submitted_at": variant.submitted_at,
        "reviewed_at": variant.reviewed_at,
        "approved_at": variant.approved_at,
        "published_at": variant.published_at,
        "questions": [
            serialize_question(question)
            for question in questions
        ],
    }


def build_manifest(
    variants: list[Variant],
    user: User,
) -> dict[str, Any]:
    """
    Builds metadata describing the export.
    """
    return {
        "format": "MODO_VARIANT_EXPORT",
        "version": 1,
        "generated_at": datetime.now(
            timezone.utc
        ),
        "generated_by": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
        },
        "variant_count": len(variants),
        "question_count": sum(
            len(variant.questions)
            for variant in variants
        ),
        "variant_ids": [
            variant.id
            for variant in variants
        ],
    }


def add_variant_media(
    archive: zipfile.ZipFile,
    variants: list[Variant],
) -> list[dict[str, Any]]:
    """
    Downloads original media files from R2
    and adds them to the ZIP archive.

    A failure for one media file does not stop
    the complete export. Such errors are returned
    for writing to media_errors.json.
    """
    client = create_s3_client()
    bucket = get_r2_bucket_name()

    errors: list[dict[str, Any]] = []
    used_paths: set[str] = set()

    for variant in variants:
        questions = sorted(
            variant.questions,
            key=lambda question: (
                question.order_number or 0,
                question.id,
            ),
        )

        for question in questions:
            media_files = sorted(
                question.media_files,
                key=lambda media: media.id,
            )

            for media in media_files:
                filename = safe_archive_name(
                    media.original_filename,
                    f"media_{media.id}",
                )

                archive_path = (
                    f"media/"
                    f"variant_{variant.id}/"
                    f"question_"
                    f"{question.order_number}_"
                    f"{question.id}/"
                    f"{filename}"
                )

                if archive_path in used_paths:
                    archive_path = (
                        f"media/"
                        f"variant_{variant.id}/"
                        f"question_"
                        f"{question.order_number}_"
                        f"{question.id}/"
                        f"{media.id}_{filename}"
                    )

                used_paths.add(archive_path)

                try:
                    object_key = normalize_r2_key(
                        media.r2_key
                    )

                    response = client.get_object(
                        Bucket=bucket,
                        Key=object_key,
                    )

                    body = response["Body"]

                    try:
                        file_data = body.read()
                    finally:
                        body.close()

                    archive.writestr(
                        archive_path,
                        file_data,
                    )

                except Exception as error:
                    logger.exception(
                        (
                            "Failed to export media. "
                            "variant_id=%s "
                            "question_id=%s "
                            "media_id=%s"
                        ),
                        variant.id,
                        question.id,
                        media.id,
                    )

                    errors.append(
                        {
                            "variant_id": variant.id,
                            "question_id": question.id,
                            "media_id": media.id,
                            "original_filename": (
                                media.original_filename
                            ),
                            "r2_key": media.r2_key,
                            "error": str(error),
                        }
                    )

    return errors


def add_legacy_media(
    archive: zipfile.ZipFile,
    questions: list[Question],
) -> None:
    """
    Adds media files for the legacy question export.
    """
    client = create_s3_client()
    bucket = get_r2_bucket_name()

    used_paths: set[str] = set()

    for question in questions:
        media_files = sorted(
            question.media_files,
            key=lambda media: media.id,
        )

        for media in media_files:
            filename = safe_archive_name(
                media.original_filename,
                f"media_{media.id}",
            )

            archive_path = (
                f"media/"
                f"question_{question.id}/"
                f"{filename}"
            )

            if archive_path in used_paths:
                archive_path = (
                    f"media/"
                    f"question_{question.id}/"
                    f"{media.id}_{filename}"
                )

            used_paths.add(archive_path)

            try:
                object_key = normalize_r2_key(
                    media.r2_key
                )

                response = client.get_object(
                    Bucket=bucket,
                    Key=object_key,
                )

                body = response["Body"]

                try:
                    file_data = body.read()
                finally:
                    body.close()

                archive.writestr(
                    archive_path,
                    file_data,
                )

            except Exception:
                logger.exception(
                    (
                        "Legacy media export failed. "
                        "question_id=%s media_id=%s"
                    ),
                    question.id,
                    media.id,
                )


@router.post(
    "/zip",
)
def export_zip(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_legacy_export
    ),
):
    """
    Legacy ZIP export of individual questions.
    """
    question_ids = normalize_ids(
        payload.question_ids
    )

    if not question_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Не выбраны вопросы "
                "для экспорта."
            ),
        )

    questions = (
        db.query(Question)
        .options(
            joinedload(
                Question.author
            ),
            selectinload(
                Question.media_files
            ),
        )
        .filter(
            Question.id.in_(question_ids),
            Question.status
            == QuestionStatus.IN_BANK,
        )
        .all()
    )

    questions_by_id = {
        question.id: question
        for question in questions
    }

    ordered_questions = [
        questions_by_id[question_id]
        for question_id in question_ids
        if question_id in questions_by_id
    ]

    if not ordered_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Утверждённые вопросы "
                "не найдены."
            ),
        )

    latex_errors: list[
        dict[str, Any]
    ] = []

    for question in ordered_questions:
        issues = validate_question_latex(
            question.title,
            question.body,
            question.options or [],
            question.explanation,
        )

        if issues:
            latex_errors.append(
                {
                    "question_id": question.id,
                    "title": question.title,
                    "issues": [
                        {
                            "line": issue.line,
                            "msg": issue.message,
                        }
                        for issue in issues
                    ],
                }
            )

    if latex_errors:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "message": (
                    "Найдены ошибки LaTeX. "
                    "Исправьте их перед экспортом."
                ),
                "errors": latex_errors,
            },
        )

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "registry.xlsx",
            generate_registry_xlsx(
                ordered_questions
            ),
        )

        archive.writestr(
            "test_bank.pdf",
            generate_test_bank_pdf(
                ordered_questions
            ),
        )

        add_legacy_media(
            archive,
            ordered_questions,
        )

    buffer.seek(0)

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"test_export_{timestamp}.zip"
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
        },
    )


@router.post(
    "/variants/zip",
)
def export_variants_zip(
    payload: VariantExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_curator
    ),
):
    """
    Exports complete variants from the bank.

    Only variants with status IN_BANK
    can be exported.

    The curator has global access
    to variants from all subjects.
    """
    variant_ids = normalize_ids(
        payload.variant_ids
    )

    if not variant_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Не выбраны варианты "
                "для экспорта."
            ),
        )

    variants = (
        db.query(Variant)
        .options(
            joinedload(
                Variant.subject
            ),
            joinedload(
                Variant.developer
            ),
            joinedload(
                Variant.reviewer
            ),
            joinedload(
                Variant.curator
            ),
            selectinload(
                Variant.questions
            ).selectinload(
                Question.media_files
            ),
        )
        .filter(
            Variant.id.in_(variant_ids),
            Variant.status
            == VariantStatus.IN_BANK,
        )
        .all()
    )

    variants_by_id = {
        variant.id: variant
        for variant in variants
    }

    ordered_variants = [
        variants_by_id[variant_id]
        for variant_id in variant_ids
        if variant_id in variants_by_id
    ]

    missing_ids = [
        variant_id
        for variant_id in variant_ids
        if variant_id
        not in variants_by_id
    ]

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": (
                    "Некоторые варианты "
                    "не найдены в банке."
                ),
                "variant_ids": missing_ids,
            },
        )

    if not ordered_variants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Варианты в банке "
                "не найдены."
            ),
        )

    empty_variant_ids = [
        variant.id
        for variant in ordered_variants
        if not variant.questions
    ]

    if empty_variant_ids:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "message": (
                    "Невозможно экспортировать "
                    "пустые варианты."
                ),
                "variant_ids": empty_variant_ids,
            },
        )

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        write_json(
            archive,
            "manifest.json",
            build_manifest(
                ordered_variants,
                user,
            ),
        )

        write_json(
            archive,
            "variants.json",
            [
                serialize_variant(variant)
                for variant in ordered_variants
            ],
        )

        archive.writestr(
            "registry.xlsx",
            generate_variants_registry_xlsx(
                ordered_variants
            ),
        )

        archive.writestr(
            "test_bank.pdf",
            generate_variants_test_bank_pdf(
                ordered_variants
            ),
        )

        media_errors = add_variant_media(
            archive,
            ordered_variants,
        )

        if media_errors:
            write_json(
                archive,
                "media_errors.json",
                media_errors,
            )

    buffer.seek(0)

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"modo_variants_{timestamp}.zip"
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
            "X-Export-Variant-Count": str(
                len(ordered_variants)
            ),
        },
    )