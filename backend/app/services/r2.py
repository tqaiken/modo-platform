"""
Cloudflare R2 S3-compatible storage service.

Media files are uploaded without compression
or image transformation. Original bytes are preserved.

Existing R2 object structure:
    modo-platform-media/questions/{question_id}/media/{file}
"""

import logging
import mimetypes
import uuid
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from fastapi import (
    HTTPException,
    UploadFile,
    status,
)

from app.core.config import get_settings


logger = logging.getLogger(__name__)

settings = get_settings()


ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/bmp",
    "image/tiff",
}


CONTENT_TYPE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


MAX_FILE_SIZE = 50 * 1024 * 1024


def require_setting(
    name: str,
    value: str | None,
) -> str:
    """
    Проверяет обязательную настройку R2.
    """
    normalized = str(
        value or ""
    ).strip()

    if not normalized:
        logger.error(
            "Required R2 setting is empty: %s",
            name,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Хранилище изображений "
                "не настроено на сервере."
            ),
        )

    return normalized


def get_r2_bucket_name() -> str:
    """
    Возвращает имя bucket R2.
    """
    return require_setting(
        "R2_BUCKET_NAME",
        settings.R2_BUCKET_NAME,
    ).strip("/")


def get_r2_public_url() -> str:
    """
    Возвращает публичный URL bucket
    без завершающего слеша.
    """
    public_url = require_setting(
        "R2_PUBLIC_URL",
        settings.R2_PUBLIC_URL,
    )

    return public_url.rstrip("/")


def get_r2_key_prefix() -> str:
    """
    Возвращает префикс существующей
    структуры объектов.

    В текущем bucket ключи имеют формат:
        modo-platform-media/questions/...
    """
    return get_r2_bucket_name()


def normalize_r2_key(
    r2_key: str,
) -> str:
    """
    Возвращает фактический object key.

    Поддерживаются оба формата записей БД:

    Старый:
        questions/3/media/file.jpeg

    Фактический:
        modo-platform-media/questions/3/media/file.jpeg
    """
    normalized_key = str(
        r2_key or ""
    ).strip().lstrip("/")

    if not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "У медиафайла отсутствует ключ R2."
            ),
        )

    key_prefix = (
        get_r2_key_prefix()
    )

    expected_prefix = (
        f"{key_prefix}/"
    )

    if normalized_key.startswith(
        expected_prefix
    ):
        return normalized_key

    return (
        f"{expected_prefix}"
        f"{normalized_key}"
    )


def normalize_filename(
    filename: str | None,
) -> str:
    """
    Убирает путь из имени входного файла.
    """
    if not filename:
        return "image"

    normalized = Path(
        filename
    ).name.strip()

    return normalized or "image"


def get_safe_extension(
    filename: str | None,
    content_type: str,
) -> str:
    """
    Определяет безопасное расширение
    по разрешённому MIME-типу.
    """
    known_extension = (
        CONTENT_TYPE_EXTENSIONS.get(
            content_type
        )
    )

    if known_extension:
        return known_extension

    guessed_extension = (
        mimetypes.guess_extension(
            content_type
        )
    )

    if guessed_extension:
        return guessed_extension.lower()

    original_suffix = Path(
        normalize_filename(
            filename
        )
    ).suffix.lower()

    if (
        original_suffix
        and len(original_suffix) <= 10
        and original_suffix[1:].isalnum()
    ):
        return original_suffix

    return ".bin"


def build_media_key(
    question_id: int,
    extension: str,
) -> str:
    """
    Формирует canonical object key.

    Новые объекты сохраняются в той же
    структуре, что и существующие:

        modo-platform-media/
        questions/{question_id}/media/{file}
    """
    if question_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Некорректный идентификатор вопроса."
            ),
        )

    normalized_extension = (
        extension
        if extension.startswith(".")
        else f".{extension}"
    )

    unique_name = (
        f"{uuid.uuid4().hex}"
        f"{normalized_extension}"
    )

    return (
        f"{get_r2_key_prefix()}/"
        f"questions/{question_id}/media/"
        f"{unique_name}"
    )


def build_public_url(
    r2_key: str,
) -> str:
    """
    Строит публичный URL по фактическому
    object key.

    Слеши сохраняются, специальные символы
    кодируются безопасно.
    """
    normalized_key = normalize_r2_key(
        r2_key
    )

    encoded_key = quote(
        normalized_key,
        safe="/",
    )

    return (
        f"{get_r2_public_url()}/"
        f"{encoded_key}"
    )


def create_s3_client():
    """
    Создаёт клиент Cloudflare R2
    после проверки конфигурации.
    """
    endpoint_url = require_setting(
        "R2_ENDPOINT_URL",
        settings.R2_ENDPOINT_URL,
    ).rstrip("/")

    access_key_id = require_setting(
        "R2_ACCESS_KEY_ID",
        settings.R2_ACCESS_KEY_ID,
    )

    secret_access_key = require_setting(
        "R2_SECRET_ACCESS_KEY",
        settings.R2_SECRET_ACCESS_KEY,
    )

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=(
            access_key_id
        ),
        aws_secret_access_key=(
            secret_access_key
        ),
        config=Config(
            signature_version="s3v4",
            retries={
                "max_attempts": 3,
                "mode": "standard",
            },
            connect_timeout=15,
            read_timeout=60,
        ),
        region_name="auto",
    )


async def upload_media_file(
    file: UploadFile,
    question_id: int,
) -> dict:
    """
    Загружает изображение в R2
    без преобразования.

    После put_object выполняется head_object.
    Метаданные возвращаются только после
    подтверждения существования объекта.
    """
    content_type = str(
        file.content_type or ""
    ).lower().strip()

    if (
        content_type
        not in ALLOWED_CONTENT_TYPES
    ):
        allowed_types = ", ".join(
            sorted(
                ALLOWED_CONTENT_TYPES
            )
        )

        raise HTTPException(
            status_code=(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),
            detail=(
                f"Тип файла "
                f"'{content_type or 'unknown'}' "
                "не разрешён. "
                f"Допустимые типы: "
                f"{allowed_types}."
            ),
        )

    original_filename = (
        normalize_filename(
            file.filename
        )
    )

    content = await file.read()

    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Загруженный файл пуст."
            ),
        )

    if file_size > MAX_FILE_SIZE:
        max_size_mb = (
            MAX_FILE_SIZE
            // 1024
            // 1024
        )

        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "Размер файла превышает "
                f"{max_size_mb} МБ."
            ),
        )

    extension = get_safe_extension(
        original_filename,
        content_type,
    )

    r2_key = build_media_key(
        question_id,
        extension,
    )

    bucket_name = (
        get_r2_bucket_name()
    )

    client = create_s3_client()

    try:
        client.put_object(
            Bucket=bucket_name,
            Key=r2_key,
            Body=content,
            ContentType=content_type,
            ContentLength=file_size,
            CacheControl=(
                "public, "
                "max-age=31536000, "
                "immutable"
            ),
            Metadata={
                "original-filename": (
                    original_filename.encode(
                        "ascii",
                        errors="ignore",
                    ).decode("ascii")
                    or "image"
                ),
                "question-id": str(
                    question_id
                ),
            },
        )

        head_response = (
            client.head_object(
                Bucket=bucket_name,
                Key=r2_key,
            )
        )

        stored_size = int(
            head_response.get(
                "ContentLength",
                -1,
            )
        )

        if stored_size != file_size:
            logger.error(
                (
                    "R2 size mismatch for key %s: "
                    "expected=%s actual=%s"
                ),
                r2_key,
                file_size,
                stored_size,
            )

            try:
                client.delete_object(
                    Bucket=bucket_name,
                    Key=r2_key,
                )
            except (
                BotoCoreError,
                ClientError,
            ):
                logger.exception(
                    (
                        "Failed to remove invalid "
                        "R2 object %s"
                    ),
                    r2_key,
                )

            raise HTTPException(
                status_code=(
                    status.HTTP_502_BAD_GATEWAY
                ),
                detail=(
                    "Хранилище не подтвердило "
                    "корректную загрузку изображения."
                ),
            )

    except HTTPException:
        raise

    except ClientError as error:
        error_data = (
            error.response.get(
                "Error",
                {},
            )
        )

        error_code = str(
            error_data.get(
                "Code",
                "Unknown",
            )
        )

        logger.exception(
            (
                "Cloudflare R2 rejected upload. "
                "bucket=%s key=%s code=%s"
            ),
            bucket_name,
            r2_key,
            error_code,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Не удалось загрузить изображение "
                "в файловое хранилище."
            ),
        ) from error

    except BotoCoreError as error:
        logger.exception(
            (
                "Cloudflare R2 connection failed. "
                "bucket=%s key=%s"
            ),
            bucket_name,
            r2_key,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Файловое хранилище временно "
                "недоступно."
            ),
        ) from error

    finally:
        await file.close()

    public_url = build_public_url(
        r2_key
    )

    return {
        "r2_key": r2_key,
        "public_url": public_url,
        "content_type": content_type,
        "file_size": file_size,
        "original_filename": (
            original_filename
        ),
    }


def media_file_exists(
    r2_key: str,
) -> bool:
    """
    Проверяет существование объекта
    по фактическому ключу R2.
    """
    try:
        normalized_key = normalize_r2_key(
            r2_key
        )
    except HTTPException:
        return False

    client = create_s3_client()

    try:
        client.head_object(
            Bucket=get_r2_bucket_name(),
            Key=normalized_key,
        )

        return True

    except ClientError as error:
        error_code = str(
            error.response.get(
                "Error",
                {},
            ).get(
                "Code",
                "",
            )
        )

        http_status = (
            error.response.get(
                "ResponseMetadata",
                {},
            ).get(
                "HTTPStatusCode"
            )
        )

        if (
            error_code in {
                "404",
                "NoSuchKey",
                "NotFound",
            }
            or http_status == 404
        ):
            return False

        logger.exception(
            (
                "Failed to check R2 object. "
                "key=%s code=%s status=%s"
            ),
            normalized_key,
            error_code,
            http_status,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Не удалось проверить изображение "
                "в файловом хранилище."
            ),
        ) from error

    except BotoCoreError as error:
        logger.exception(
            "R2 check failed for key=%s",
            normalized_key,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Файловое хранилище временно "
                "недоступно."
            ),
        ) from error


def delete_media_file(
    r2_key: str,
) -> None:
    """
    Удаляет объект из R2
    по фактическому ключу.

    Поддерживает старые записи БД,
    где ключ начинается с questions/.
    """
    normalized_key = normalize_r2_key(
        r2_key
    )

    client = create_s3_client()

    try:
        client.delete_object(
            Bucket=get_r2_bucket_name(),
            Key=normalized_key,
        )

    except (
        BotoCoreError,
        ClientError,
    ) as error:
        logger.exception(
            (
                "Failed to delete R2 object. "
                "key=%s"
            ),
            normalized_key,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Не удалось удалить изображение "
                "из файлового хранилища."
            ),
        ) from error


def generate_presigned_url(
    r2_key: str,
    expires_in: int = 3600,
) -> str:
    """
    Создаёт временную подписанную ссылку
    по фактическому ключу R2.
    """
    normalized_key = normalize_r2_key(
        r2_key
    )

    normalized_expiration = max(
        60,
        min(
            int(expires_in),
            604800,
        ),
    )

    client = create_s3_client()

    try:
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": (
                    get_r2_bucket_name()
                ),
                "Key": normalized_key,
            },
            ExpiresIn=(
                normalized_expiration
            ),
        )

    except (
        BotoCoreError,
        ClientError,
    ) as error:
        logger.exception(
            (
                "Failed to create "
                "presigned URL. key=%s"
            ),
            normalized_key,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Не удалось создать ссылку "
                "на изображение."
            ),
        ) from error