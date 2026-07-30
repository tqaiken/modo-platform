from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.user import User, UserRole
from app.models.question import Question, QuestionStatus
from app.models.media import MediaFile
from app.schemas.media import MediaFileRead
from app.services.r2 import upload_media_file, delete_media_file

router = APIRouter(prefix="/media")

require_developer = RoleGuard(UserRole.DEVELOPER)


@router.post("/upload/{question_id}", response_model=MediaFileRead, status_code=201)
async def upload_file(
    question_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """Upload a media file for a question. Original quality preserved in R2."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    if q.author_id != user.id:
        raise HTTPException(403, "Not your question")
    if q.status not in (QuestionStatus.DRAFT, QuestionStatus.REVISION):
        raise HTTPException(400, "Can only upload to DRAFT/REVISION questions")

    # Upload to R2
    result = await upload_media_file(file, question_id)

    # Save metadata to DB
    media = MediaFile(
        question_id=question_id,
        original_filename=result["original_filename"],
        r2_key=result["r2_key"],
        content_type=result["content_type"],
        file_size=result["file_size"],
        public_url=result["public_url"],
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


@router.delete("/{media_id}", status_code=204)
def delete_file(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_developer),
):
    """Delete a media file."""
    media = db.query(MediaFile).filter(MediaFile.id == media_id).first()
    if not media:
        raise HTTPException(404, "Media file not found")

    q = db.query(Question).filter(Question.id == media.question_id).first()
    if q.author_id != user.id:
        raise HTTPException(403, "Not your question")

    # Delete from R2 and DB
    delete_media_file(media.r2_key)
    db.delete(media)
    db.commit()
