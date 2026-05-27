"""Image storage abstraction over local filesystem (dev) and Cloudflare R2 (prod).

The active backend is chosen by ENVIRONMENT: local dev writes under ./data/images
and serves files by path; production uploads to an R2 bucket via boto3 and serves
from the public R2 URL. ``process_uploaded_image`` validates, resizes, and
re-encodes uploads before they reach either backend.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Protocol
from uuid import UUID

import boto3
from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_LONGEST_SIDE = 1600
JPEG_QUALITY = 88
ALLOWED_INPUT_FORMATS = {"JPEG", "PNG", "WEBP"}


class StorageError(Exception):
    """Raised when an upload is invalid or a storage backend operation fails."""


class ImageStorage(Protocol):
    def upload(self, key: str, image_bytes: bytes, content_type: str) -> str: ...

    def download(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def get_url(self, key: str) -> str: ...


class LocalImageStorage:
    """Filesystem-backed storage for local development."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or (Path("data") / "images")

    def upload(self, key: str, image_bytes: bytes, content_type: str) -> str:
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        return self.get_url(key)

    def download(self, key: str) -> bytes:
        path = self.base_dir / key
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageError(f"Local read failed for {key}: {exc}") from exc

    def delete(self, key: str) -> None:
        path = self.base_dir / key
        if path.exists():
            path.unlink()

    def get_url(self, key: str) -> str:
        return str((self.base_dir / key).resolve())


class R2ImageStorage:
    """Cloudflare R2 (S3-compatible) storage for production."""

    def __init__(
        self,
        client: object | None = None,
        bucket: str | None = None,
        public_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self.bucket = bucket or settings.r2_bucket
        self.public_url = (public_url or settings.r2_public_url).rstrip("/")
        self.client = client or boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )

    def upload(self, key: str, image_bytes: bytes, content_type: str) -> str:
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=key, Body=image_bytes, ContentType=content_type
            )
        except Exception as exc:
            raise StorageError(f"R2 upload failed for {key}: {exc}") from exc
        return self.get_url(key)

    def download(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as exc:
            raise StorageError(f"R2 download failed for {key}: {exc}") from exc

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise StorageError(f"R2 delete failed for {key}: {exc}") from exc

    def get_url(self, key: str) -> str:
        return f"{self.public_url}/{key}"


def get_storage() -> ImageStorage:
    """Return the storage backend for the current environment."""
    if get_settings().environment == "local":
        return LocalImageStorage()
    return R2ImageStorage()


def _extract_bytes(uploaded_file: object) -> bytes:
    if isinstance(uploaded_file, bytes | bytearray):
        return bytes(uploaded_file)
    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()
    if hasattr(uploaded_file, "read"):
        return uploaded_file.read()
    raise StorageError(f"Unsupported uploaded_file type: {type(uploaded_file)!r}")


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)


def process_uploaded_image(
    uploaded_file: object, user_id: UUID, item_id: UUID
) -> tuple[bytes, str, str]:
    """Validate, resize, and re-encode an upload.

    Returns ``(image_bytes, key, content_type)``. Images wider/taller than
    ``MAX_LONGEST_SIDE`` are downscaled (LANCZOS, aspect preserved). Output is
    PNG when the source has alpha, otherwise JPEG at quality 88.

    Raises:
        StorageError: if the upload exceeds 5MB, is unreadable, or is not a
            JPEG/PNG/WEBP image.
    """
    data = _extract_bytes(uploaded_file)
    if len(data) > MAX_UPLOAD_BYTES:
        raise StorageError("Image exceeds the 5MB upload limit")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as exc:
        raise StorageError(f"Uploaded file is not a readable image: {exc}") from exc

    if image.format not in ALLOWED_INPUT_FORMATS:
        raise StorageError(f"Unsupported image format {image.format!r}; allowed: JPEG, PNG, WEBP")

    width, height = image.size
    longest = max(width, height)
    if longest > MAX_LONGEST_SIDE:
        scale = MAX_LONGEST_SIDE / longest
        image = image.resize((round(width * scale), round(height * scale)), Image.LANCZOS)

    buffer = io.BytesIO()
    if _has_alpha(image):
        image.convert("RGBA").save(buffer, format="PNG", optimize=True)
        ext, content_type = "png", "image/png"
    else:
        image.convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY)
        ext, content_type = "jpg", "image/jpeg"

    key = f"items/{user_id}/{item_id}.{ext}"
    return buffer.getvalue(), key, content_type
