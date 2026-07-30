from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.question import QuestionStatus, Language
from app.models.log import LogAction
from app.schemas.user import UserRead
from app.schemas.media import MediaFileRead
from app.schemas.comment import CommentRead


class QuestionOption(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False


class QuestionCreate(BaseModel):
    title: str = Field(min_length=5, max_length=500)
    body: str = Field(min_length=1)  # supports LaTeX $...$
    options: list[QuestionOption] = Field(min_length=2, max_length=10)
    explanation: Optional[str] = None
    language: Language = Language.RU
    subject_id: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: int = Field(default=1, ge=1, le=5)


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    body: Optional[str] = None
    options: Optional[list[QuestionOption]] = None
    explanation: Optional[str] = None
    language: Optional[Language] = None
    subject_id: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)


class QuestionSubmit(BaseModel):
    """Developer submits question for verification."""
    pass  # no extra fields — just a status transition


class QuestionReview(BaseModel):
    """Verifier approves or rejects (optionally editing the question)."""
    approved: bool
    comment: str = Field(min_length=1, max_length=5000)
    # Optional: verifier can edit question text inline
    edited_title: Optional[str] = None
    edited_body: Optional[str] = None
    edited_options: Optional[list[QuestionOption]] = None
    edited_explanation: Optional[str] = None


class QuestionRead(BaseModel):
    id: int
    title: str
    body: str
    body_html: Optional[str] = None
    options: list[dict]
    explanation: Optional[str] = None
    language: Language = Language.RU
    subject_id: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: int
    status: QuestionStatus

    author: UserRead
    reviewer: Optional[UserRead] = None

    media_files: list[MediaFileRead] = []
    comments: list[CommentRead] = []
    logs: list["LogRead"] = []

    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class QuestionList(BaseModel):
    items: list[QuestionRead]
    total: int
    page: int
    page_size: int


class LogRead(BaseModel):
    id: int
    action: LogAction
    details: Optional[str] = None
    user: UserRead
    timestamp: datetime

    model_config = {"from_attributes": True}
