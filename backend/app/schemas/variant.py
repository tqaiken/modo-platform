from datetime import datetime

from pydantic import BaseModel, Field

from app.models.variant import VariantStatus


class VariantCreate(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=500,
        description="Название или код варианта",
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class VariantUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=500,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class VariantRead(BaseModel):
    id: int
    title: str
    description: str | None

    subject_id: int | None
    developer_id: int

    status: VariantStatus
    question_count: int = 0

    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    reviewed_at: datetime | None
    approved_at: datetime | None

    model_config = {
        "from_attributes": True,
    }


class VariantList(BaseModel):
    items: list[VariantRead]
    total: int
    page: int
    page_size: int


class VariantDashboard(BaseModel):
    total_variants: int
    draft_variants: int
    verification_variants: int
    revision_variants: int
    approved_variants: int
    bank_variants: int
    total_questions: int