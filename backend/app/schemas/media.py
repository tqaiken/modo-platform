from datetime import datetime
from pydantic import BaseModel


class MediaFileRead(BaseModel):
    id: int
    original_filename: str
    r2_key: str
    content_type: str
    file_size: int
    width: int | None = None
    height: int | None = None
    public_url: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}
