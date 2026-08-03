from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.media import MediaFile
from app.models.question import Question
from app.models.user import User, UserRole
from app.models.variant import VariantStatus
from app.schemas.media import MediaFileRead
from app.services.r2 import (
    delete_media_file,
    upload_media_file,
)


router = APIRouter(prefix="/media")


require_developer = RoleGuard(
    UserRole.DEVELOPER
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

    Чужой или отсутствующий вопрос возвращается как 404,
    чтобы не раскрывать существование чужих материалов.
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


def ensure_media_editable(
    question: Question,
) -> None:
    """
    Проверяет возможность изменения медиафайлов.

    Для нового процесса вопрос должен находиться
    внутри варианта со статусом DRAFT или REVISION.
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
    user: User = Depends(require_developer),
):
    """
    Загружает изображение вопроса в Cloudflare R2.

    Исходное качество файла сохраняется.
    """
    question = get_developer_question_or_404(
        db,
        question_id,
        user,
    )

    ensure_media_editable(question)

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось определить тип файла.",
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Разрешена загрузка только "
                "изображений."
            ),
        )

    result = await upload_media_file(
        file,
        question_id,
    )

    media = MediaFile(
        question_id=question_id,
        original_filename=result[
            "original_filename"
        ],
        r2_key=result["r2_key"],
        content_type=result["content_type"],
        file_size=result["file_size"],
        public_url=result["public_url"],
    )

    db.add(media)
    db.commit()
    db.refresh(media)

    return media


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_file(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """
    Удаляет изображение из Cloudflare R2
    и его метаданные из PostgreSQL.
    """
    media = (
        db.query(MediaFile)
        .filter(MediaFile.id == media_id)
        .first()
    )

    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Медиафайл не найден.",
        )

    question = get_developer_question_or_404(
        db,
        media.question_id,
        user,
    )

    ensure_media_editable(question)

    delete_media_file(media.r2_key)

    db.delete(media)
    db.commit()

    return None