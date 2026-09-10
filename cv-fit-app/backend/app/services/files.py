import logging
from typing import Any

from pydantic import ValidationError

from app.core.config import RAW_EXTRACTION_BUCKET
from app.models.cv_raw_extraction import (
    RAW_EXTRACTION_CONTENT_TYPE,
    InvalidRawExtractionArtifactError,
    RawExtraction,
)
from app.repositories.files import FileRepository
from app.storage.base import Storage

logger = logging.getLogger(__name__)


# Buckets that may hold genuine raw-extraction rows. "cv" is legacy: a
# misconfiguration window stored raw artifacts alongside source PDFs.
# Content-type is the real gate; the bucket allowlist only preserves access
# to those legacy rows.
_RAW_ARTIFACT_BUCKETS = frozenset({RAW_EXTRACTION_BUCKET, "cv"})


class FileService:
    """Service handling file operations via Storage protocol and FileRepository."""

    def __init__(
        self,
        storage: Storage,
        repository: FileRepository | None = None,
    ):
        self.storage = storage
        self.repository = repository or FileRepository()

    async def upload_file(
        self,
        user_id: str,
        filename: str,
        data: bytes,
        content_type: str,
        bucket: str = "user-files",
        include_url: bool = True,
        original_filename: str | None = None,
    ) -> dict[str, Any]:
        """Upload file content to object storage and record neutral metadata in DB."""
        path = f"{user_id}/{filename}"
        original_name = original_filename or filename

        # 1. Upload to storage provider
        await self.storage.upload(
            bucket=bucket,
            path=path,
            data=data,
            content_type=content_type,
        )

        # 2. Store neutral metadata in database. If metadata persistence fails,
        # roll back the just-uploaded object so private content is not left
        # without an ownership-checked server record.
        try:
            record = await self.repository.create_file(
                user_id=user_id,
                bucket=bucket,
                object_path=path,
                original_filename=original_name,
                content_type=content_type,
            )
            if (
                not isinstance(record, dict)
                or not record.get("id")
                or str(record.get("user_id")) != str(user_id)
                or record.get("bucket") != bucket
                or record.get("object_path") != path
                or record.get("original_filename") != original_name
                or record.get("content_type") != content_type
            ):
                raise RuntimeError("File metadata could not be persisted.")
        except Exception:
            try:
                await self.storage.delete(bucket=bucket, path=path)
            except Exception:
                logger.error(
                    "Failed to roll back file after metadata persistence error"
                )
            raise

        if not include_url:
            return record

        # 3. Attach a signed URL for caller-visible source files. On failure,
        # roll back object + metadata so no unreachable phantom rows/objects
        # accumulate (a row without a working URL is worse than no row).
        try:
            preview_url = await self.storage.create_signed_url(
                bucket=bucket, path=path, expires_in=3600
            )
        except Exception:
            try:
                await self.storage.delete(bucket=bucket, path=path)
            except Exception:
                logger.error("Failed to roll back file object after URL mint failure")
            try:
                if isinstance(record, dict) and record.get("id"):
                    await self.repository.delete_file(record["id"])
            except Exception:
                logger.error("Failed to roll back file metadata after URL mint failure")
            raise
        return {**record, "url": preview_url}

    async def get_owned_file_url(self, user_id: str, file_id: str) -> str | None:
        """Mint an accessible URL for a caller-owned file, else None.

        Ownership is re-checked here so callers holding only a file id
        (e.g. a pdf_file_id stored on a user_cvs row) can never mint URLs
        for another user's objects. Signed URLs work on private buckets.
        """
        record = await self.repository.get_file_by_id(file_id)
        if not record or str(record["user_id"]) != str(user_id):
            return None
        if record.get("content_type") == RAW_EXTRACTION_CONTENT_TYPE:
            # Raw artifacts are server-only (download path), even when a
            # legacy row stores them outside the raw bucket.
            return None
        return await self.storage.create_signed_url(
            bucket=record["bucket"],
            path=record["object_path"],
        )

    async def delete_owned_file(self, user_id: str, file_id: str) -> bool:
        """Best-effort delete of a caller-owned file; never raises."""
        try:
            record = await self.repository.get_file_by_id(file_id)
            if not record or str(record["user_id"]) != str(user_id):
                return False
            try:
                await self.storage.delete(
                    bucket=record["bucket"],
                    path=record["object_path"],
                )
            except Exception:
                logger.warning(
                    "Owned file object delete failed; removing metadata anyway.",
                    exc_info=True,
                )
            return await self.repository.delete_file(file_id)
        except Exception:
            logger.warning("Owned file delete failed.", exc_info=True)
            return False

    async def load_raw_extraction(
        self,
        user_id: str,
        file_id: str,
    ) -> RawExtraction | None:
        """Load and validate an ownership-checked private raw extraction."""
        record = await self.repository.get_file_by_id(file_id)
        if not record or str(record["user_id"]) != str(user_id):
            return None
        if (
            record.get("bucket") not in _RAW_ARTIFACT_BUCKETS
            or record.get("content_type") != RAW_EXTRACTION_CONTENT_TYPE
        ):
            return None
        payload = await self.storage.download(
            bucket=record["bucket"],
            path=record["object_path"],
        )
        try:
            return RawExtraction.model_validate_json(payload)
        except ValidationError as exc:
            raise InvalidRawExtractionArtifactError(
                "Stored raw extraction failed schema validation."
            ) from exc

    async def delete_raw_extraction(self, user_id: str, file_id: str) -> bool:
        """Delete only an ownership-checked raw extraction artifact."""
        record = await self.repository.get_file_by_id(file_id)
        if not record or str(record["user_id"]) != str(user_id):
            return False
        if (
            record.get("bucket") not in _RAW_ARTIFACT_BUCKETS
            or record.get("content_type") != RAW_EXTRACTION_CONTENT_TYPE
        ):
            return False
        await self.storage.delete(
            bucket=record["bucket"],
            path=record["object_path"],
        )
        return await self.repository.delete_file(file_id)

    async def delete_file(self, user_id: str, file_id: str) -> bool:
        """Delete file from object storage and database after verifying ownership."""
        record = await self.repository.get_file_by_id(file_id)
        if not record or str(record["user_id"]) != str(user_id):
            return False

        # 1. Delete from storage provider
        await self.storage.delete(
            bucket=record["bucket"],
            path=record["object_path"],
        )

        # 2. Delete metadata record from database
        return await self.repository.delete_file(file_id)
