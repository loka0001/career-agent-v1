"""Validated image storage adapters."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.models import MediaAssetModel
from app.domain.errors import ExternalProviderError
from app.security import create_signed_resource_token

PRIVATE_MEDIA_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class StoredImage:
    original_url: str
    public_url: str | None


class ImageStorage(Protocol):
    def store(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage: ...

    def store_media(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage: ...


class LocalImageStorage:
    def __init__(self, directory: Path, public_base_url: str, secret_key: str):
        self._directory = directory
        self._public_base_url = public_base_url.rstrip("/")
        self._secret_key = secret_key

    def _write(self, directory: Path, content: bytes, mime_type: str) -> str:
        directory.mkdir(parents=True, exist_ok=True)
        self._directory.mkdir(parents=True, exist_ok=True)
        suffix = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "audio/aac": ".aac",
            "audio/mp4": ".m4a",
            "audio/mpeg": ".mp3",
            "audio/amr": ".amr",
            "audio/ogg": ".ogg",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
        }.get(mime_type, ".bin")
        filename = f"{uuid.uuid4().hex}{suffix}"
        destination = directory / filename
        destination.write_bytes(content)
        return filename

    def store(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage:
        del store_id
        filename = self._write(self._directory, content, mime_type)
        url = f"{self._public_base_url}/uploads/{filename}"
        return StoredImage(original_url=url, public_url=None)

    def store_media(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage:
        private_directory = self._directory / "private"
        filename = self._write(private_directory, content, mime_type)
        resource = f"local-media:{store_id}:{filename}"
        token = create_signed_resource_token(
            resource,
            ttl_seconds=PRIVATE_MEDIA_TTL_SECONDS,
            secret_key=self._secret_key,
        )
        url = f"{self._public_base_url}/private-media/{store_id}/{filename}?token={token}"
        return StoredImage(original_url=url, public_url=None)


class CloudinaryImageStorage:
    def __init__(self, settings: Settings):
        import cloudinary

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key.get_secret_value(),
            api_secret=settings.cloudinary_api_secret.get_secret_value(),
            secure=True,
            timeout=settings.cloudinary_timeout_seconds,
        )

    def store(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage:
        del store_id
        resource_type = "image" if mime_type.startswith("image/") else "auto"
        try:
            from cloudinary.uploader import upload

            result = upload(
                content,
                folder="commerce-ai/products",
                resource_type=resource_type,
            )
            url = str(result["secure_url"])
            return StoredImage(original_url=url, public_url=url)
        except Exception as exc:
            raise ExternalProviderError("Cloudinary upload failed") from exc

    def store_media(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage:
        resource_type = "image" if mime_type.startswith("image/") else "raw"
        try:
            from cloudinary import utils
            from cloudinary.uploader import upload

            result = upload(
                content,
                folder=f"commerce-ai/private/{store_id}",
                resource_type=resource_type,
                type="authenticated",
            )
            url, _ = utils.cloudinary_url(
                str(result["public_id"]),
                resource_type=resource_type,
                type="authenticated",
                sign_url=True,
                secure=True,
            )
            return StoredImage(original_url=str(url), public_url=None)
        except Exception as exc:
            raise ExternalProviderError("Cloudinary private upload failed") from exc


class DatabaseImageStorage:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        public_base_url: str,
        secret_key: str,
    ):
        self._session_factory = session_factory
        self._public_base_url = public_base_url.rstrip("/")
        self._secret_key = secret_key

    def _store(
        self,
        content: bytes,
        mime_type: str,
        *,
        store_id: str,
        is_public: bool,
        purpose: str,
    ) -> StoredImage:
        asset_id = uuid.uuid4().hex
        with self._session_factory.begin() as session:
            session.add(
                MediaAssetModel(
                    id=asset_id,
                    store_id=store_id,
                    mime_type=mime_type,
                    content=content,
                    byte_size=len(content),
                    is_public=is_public,
                    purpose=purpose,
                )
            )
        url = f"{self._public_base_url}/media/{asset_id}"
        if is_public:
            return StoredImage(original_url=url, public_url=url)
        token = create_signed_resource_token(
            f"database-media:{asset_id}",
            ttl_seconds=PRIVATE_MEDIA_TTL_SECONDS,
            secret_key=self._secret_key,
        )
        return StoredImage(original_url=f"{url}?token={token}", public_url=None)

    def store(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage:
        return self._store(
            content,
            mime_type,
            store_id=store_id,
            is_public=True,
            purpose="product",
        )

    def store_media(self, content: bytes, mime_type: str, *, store_id: str) -> StoredImage:
        return self._store(
            content,
            mime_type,
            store_id=store_id,
            is_public=False,
            purpose="attachment",
        )


def build_image_storage(
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> ImageStorage:
    if settings.image_storage_provider == "cloudinary":
        return CloudinaryImageStorage(settings)
    if settings.image_storage_provider == "database":
        return DatabaseImageStorage(
            session_factory,
            settings.public_base_url,
            settings.effective_secret_key,
        )
    return LocalImageStorage(
        settings.upload_directory,
        settings.public_base_url,
        settings.effective_secret_key,
    )
