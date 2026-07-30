"""
Export API — generates ZIP with registry.xlsx, test_bank.pdf, and media/ folder.
"""
import io
import zipfile
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import RoleGuard
from app.models.user import User, UserRole
from app.models.question import Question, QuestionStatus
from app.services.export_xlsx import generate_registry_xlsx
from app.services.export_pdf import generate_test_bank_pdf
from app.services.latex_validator import validate_question_latex

router = APIRouter(prefix="/export")

require_curator = RoleGuard(UserRole.CURATOR, UserRole.VERIFIER)


class ExportRequest(BaseModel):
    question_ids: list[int]


@router.post("/zip")
def export_zip(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_curator),
):
    """Generate and download a ZIP archive with registry, PDF, and media."""
    if not payload.question_ids:
        raise HTTPException(400, "No questions selected")

    # Fetch questions — only IN_BANK
    questions = (
        db.query(Question)
        .filter(
            Question.id.in_(payload.question_ids),
            Question.status == QuestionStatus.IN_BANK,
        )
        .all()
    )
    if not questions:
        raise HTTPException(404, "No approved questions found for given IDs")

    # ── Validate LaTeX in all questions before export ──
    latex_errors = []
    for q in questions:
        issues = validate_question_latex(q.title, q.body, q.options or [], q.explanation)
        if issues:
            latex_errors.append({
                "question_id": q.id,
                "title": q.title,
                "issues": [{"line": i.line, "msg": i.message} for i in issues],
            })
    if latex_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "LaTeX validation errors found. Fix them before exporting.",
                "errors": latex_errors,
            },
        )

    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. registry.xlsx
        xlsx_data = generate_registry_xlsx(questions)
        zf.writestr("registry.xlsx", xlsx_data)

        # 2. test_bank.pdf
        pdf_data = generate_test_bank_pdf(questions)
        zf.writestr("test_bank.pdf", pdf_data)

        # 3. media/ — download originals from R2
        import boto3
        from app.core.config import get_settings

        settings = get_settings()
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )

        for q in questions:
            for media in q.media_files:
                try:
                    obj = s3.get_object(Bucket=settings.R2_BUCKET_NAME, Key=media.r2_key)
                    file_data = obj["Body"].read()
                    zf.writestr(f"media/{media.original_filename}", file_data)
                except Exception:
                    pass  # skip missing files

    buf.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"test_export_{timestamp}.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
