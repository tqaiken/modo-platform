"""CRUD for subjects reference table."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.security import get_current_user, RoleGuard
from app.models.user import User, UserRole
from app.models.subject import Subject

router = APIRouter(prefix="/subjects")

require_any = RoleGuard(UserRole.DEVELOPER, UserRole.VERIFIER, UserRole.CURATOR)
require_curator = RoleGuard(UserRole.CURATOR)


class SubjectCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    title_kz: str | None = None


class SubjectRead(BaseModel):
    id: int
    code: str
    title: str
    title_kz: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SubjectRead])
def list_subjects(
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    """List all active subjects."""
    return db.query(Subject).filter(Subject.is_active == True).order_by(Subject.title).all()


@router.post("", response_model=SubjectRead, status_code=201)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_curator),
):
    """Create a new subject (curator only)."""
    existing = db.query(Subject).filter(Subject.code == payload.code).first()
    if existing:
        raise HTTPException(409, f"Subject with code '{payload.code}' already exists")

    subj = Subject(
        code=payload.code,
        title=payload.title,
        title_kz=payload.title_kz,
    )
    db.add(subj)
    db.commit()
    db.refresh(subj)
    return subj


@router.put("/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: int,
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_curator),
):
    """Update a subject (curator only)."""
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    subj.code = payload.code
    subj.title = payload.title
    subj.title_kz = payload.title_kz
    db.commit()
    db.refresh(subj)
    return subj


@router.delete("/{subject_id}", status_code=204)
def deactivate_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_curator),
):
    """Soft-delete a subject (set is_active=False)."""
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    subj.is_active = False
    db.commit()
