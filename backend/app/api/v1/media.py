import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.media import MediaFile
from app.models.question import Question
from app.models.user import User, UserRole
from app.models.variant import VariantStatus
from app.schemas.media import MediaFileRead
from app.services.r2 import (
    build_public_url,
    delete_media_file,
    media_file_exists,
    upload_media_file,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/media",
)


require_developer = RoleGuard(
    UserRole.DEVELOPER,
)


EDITABLE_VARIANT_STATUSES = {
    VariantStatus.DRAFT,
    VariantStatus.REVISION,
}


def get_developer_question_or_404(
    db: Session,
    question_id: int,
    user: User,
) -> Question:
    """
    Возвращает вопрос текущего разработчика.

    Чужой или отсутствующий вопрос возвращается
    как 404, чтобы не раскрывать существование
    чужих материалов.
    """
    question = (
        db.query(Question)
        .filter(
            Question.id == question_id,
            Question.author_id == user.id,
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос не найден.",
        )

    return question


def get_media_or_404(
    db: Session,
    media_id: int,
) -> MediaFile:
    """
    Возвращает метаданные изображения.
    """
    media = (
        db.query(MediaFile)
        .filter(
            MediaFile.id == media_id
        )
        .first()
    )

    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Медиафайл не найден.",
        )

    return media


def ensure_media_editable(
    question: Question,
) -> None:
    """
    Разрешает изменение изображений только
    у вопросов внутри варианта DRAFT или REVISION.
    """
    if question.variant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Загрузка файлов доступна только "
                "для вопросов внутри варианта."
            ),
        )

    if question.variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вариант вопроса не найден.",
        )

    if (
        question.variant.status
        not in EDITABLE_VARIANT_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Изображения можно изменять только "
                "в варианте со статусом DRAFT "
                "или REVISION."
            ),
        )


@router.post(
    "/upload/{question_id}",
    response_model=MediaFileRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    question_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    """
    Загружает изображение вопроса в R2.

    Объект сначала сохраняется и проверяется в R2.
    Только после этого метаданные записываются
    в PostgreSQL.
    """
    question = (
        get_developer_question_or_404(
            db,
            question_id,
            user,
        )
    )

    ensure_media_editable(
        question
    )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Не удалось определить тип файла."
            ),
        )

    if not file.content_type.startswith(
        "image/"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),
            detail=(
                "Разрешена загрузка только "
                "изображений."
            ),
        )

    result = await upload_media_file(
        file,
        question_id,
    )

    r2_key = str(
        result["r2_key"]
    )

    media = MediaFile(
        question_id=question_id,
        original_filename=str(
            result["original_filename"]
        ),
        r2_key=r2_key,
        content_type=str(
            result["content_type"]
        ),
        file_size=int(
            result["file_size"]
        ),
        public_url=build_public_url(
            r2_key
        ),
    )

    try:
        db.add(media)
        db.commit()
        db.refresh(media)

    except SQLAlchemyError as error:
        db.rollback()

        logger.exception(
            (
                "Failed to save media metadata. "
                "question_id=%s r2_key=%s"
            ),
            question_id,
            r2_key,
        )

        try:
            delete_media_file(
                r2_key
            )
        except HTTPException:
            logger.exception(
                (
                    "Failed to clean up R2 object "
                    "after database error. key=%s"
                ),
                r2_key,
            )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Изображение загрузилось в хранилище, "
                "но его метаданные не удалось сохранить."
            ),
        ) from error

    return media


@router.get(
    "/{media_id}",
    response_model=MediaFileRead,
)
def get_media(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    """
    Возвращает изображение текущего разработчика.

    Схема MediaFileRead автоматически пересобирает
    public_url из актуального r2_key.
    """
    media = get_media_or_404(
        db,
        media_id,
    )

    get_developer_question_or_404(
        db,
        media.question_id,
        user,
    )

    return media


@router.get(
    "/{media_id}/status",
)
def get_media_status(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    """
    Проверяет существование объекта в R2.

    Запись PostgreSQL не изменяется.
    """
    media = get_media_or_404(
        db,
        media_id,
    )

    get_developer_question_or_404(
        db,
        media.question_id,
        user,
    )

    return {
        "media_id": media.id,
        "question_id": media.question_id,
        "r2_key": media.r2_key,
        "public_url": build_public_url(
            media.r2_key
        ),
        "exists": media_file_exists(
            media.r2_key
        ),
    }


@router.patch(
    "/{media_id}/refresh-url",
    response_model=MediaFileRead,
)
def refresh_media_url(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    """
    Обновляет историческое поле public_url
    в PostgreSQL.

    Для отображения это необязательно, поскольку
    MediaFileRead уже пересобирает URL автоматически.
    """
    media = get_media_or_404(
        db,
        media_id,
    )

    question = (
        get_developer_question_or_404(
            db,
            media.question_id,
            user,
        )
    )

    ensure_media_editable(
        question
    )

    if not media_file_exists(
        media.r2_key
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Объект изображения отсутствует "
                "в файловом хранилище."
            ),
        )

    media.public_url = build_public_url(
        media.r2_key
    )

    try:
        db.commit()
        db.refresh(media)

    except SQLAlchemyError as error:
        db.rollback()

        logger.exception(
            (
                "Failed to refresh media URL. "
                "media_id=%s"
            ),
            media_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Не удалось обновить ссылку "
                "изображения."
            ),
        ) from error

    return media


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_file(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_developer
    ),
):
    """
    Удаляет изображение из R2
    и метаданные из PostgreSQL.

    normalize_r2_key внутри delete_media_file
    поддерживает существующие старые ключи.
    """
    media = get_media_or_404(
        db,
        media_id,
    )

    question = (
        get_developer_question_or_404(
            db,
            media.question_id,
            user,
        )
    )

    ensure_media_editable(
        question
    )

    delete_media_file(
        media.r2_key
    )

    try:
        db.delete(media)
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()

        logger.exception(
            (
                "R2 object was deleted, but media "
                "metadata deletion failed. "
                "media_id=%s r2_key=%s"
            ),
            media.id,
            media.r2_key,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Изображение удалено из хранилища, "
                "но запись базы данных удалить "
                "не удалось."
            ),
        ) from error

    return None