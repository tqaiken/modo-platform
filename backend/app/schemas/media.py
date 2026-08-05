from datetime import datetime

from pydantic import (
    BaseModel,
    model_validator,
)

from app.services.r2 import (
    build_public_url,
)


class MediaFileRead(BaseModel):
    """
    Представление медиафайла в API.

    public_url пересобирается из r2_key
    при каждом формировании ответа.

    Это поддерживает старые записи, где:
        r2_key = questions/.../file.png

    При этом реальный объект хранится как:
        modo-platform-media/questions/.../file.png
    """

    id: int
    original_filename: str
    r2_key: str
    content_type: str
    file_size: int

    width: int | None = None
    height: int | None = None

    public_url: str

    uploaded_at: datetime

    @model_validator(
        mode="after",
    )
    def rebuild_public_url(
        self,
    ) -> "MediaFileRead":
        """
        Не доверяет историческому public_url
        из PostgreSQL.

        Рабочий URL всегда формируется
        из текущего R2_PUBLIC_URL и r2_key.
        """
        self.public_url = build_public_url(
            self.r2_key
        )

        return self

    model_config = {
        "from_attributes": True,
    }