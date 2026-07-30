"""
Cloudflare R2 (S3-compatible) file storage service.
Uploads are stored WITHOUT compression — original quality preserved.
"""
import uuid
import boto3
from botocore.config import Config
from fastapi import UploadFile, HTTPException
from app.core.config import get_settings

settings = get_settings()

# ── S3 client configured for Cloudflare R2 ──
s3_client = boto3.client(
    "s3",
    endpoint_url=settings.R2_ENDPOINT_URL,
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    config=Config(
        signature_version="s3v4",
        retries={"max_attempts": 3},
    ),
    region_name="auto",
)

ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/bmp",
    "image/tiff",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def upload_media_file(
    file: UploadFile,
    question_id: int,
) -> dict:
    """
    Upload an image to R2 at full quality.
    Returns dict with r2_key, public_url, content_type, file_size.
    """
    # ── Validate content type ──
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    # ── Read file content ──
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size} bytes). Max: {MAX_FILE_SIZE} bytes.",
        )

    # ── Build unique R2 key ──
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    r2_key = f"questions/{question_id}/media/{unique_name}"

    # ── Upload WITHOUT any processing — original quality ──
    s3_client.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=r2_key,
        Body=content,
        ContentType=file.content_type,
        CacheControl="public, max-age=31536000",  # 1 year cache
    )

    public_url = f"{settings.R2_PUBLIC_URL}/{r2_key}"

    return {
        "r2_key": r2_key,
        "public_url": public_url,
        "content_type": file.content_type,
        "file_size": file_size,
        "original_filename": file.filename,
    }


def delete_media_file(r2_key: str) -> None:
    """Delete a file from R2."""
    try:
        s3_client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=r2_key)
    except Exception:
        pass  # best-effort deletion


def generate_presigned_url(r2_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for private files."""
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": r2_key},
        ExpiresIn=expires_in,
    )
