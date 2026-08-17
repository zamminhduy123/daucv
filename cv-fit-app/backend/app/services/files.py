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
    ) -> dict[str, Any]:
        """Upload file content to object storage and record neutral metadata in DB."""
        path = f"{user_id}/{filename}"

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
                original_filename=filename,
                content_type=content_type,
            )
            if (
                not isinstance(record, dict)
                or not record.get("id")
                or str(record.get("user_id")) != str(user_id)
                or record.get("bucket") != bucket
                or record.get("object_path") != path
                or record.get("original_filename") != filename
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

        # 3. Generate dynamic URL only for caller-visible source files.
        url = await self.storage.get_url(bucket=bucket, path=path)
        return {**record, "url": url}

    async def get_file_url(self, file_id: str) -> str | None:
        """Get accessible URL for a stored file by ID."""
        record = await self.repository.get_file_by_id(file_id)
        if not record:
            return None
        return await self.storage.get_url(
            bucket=record["bucket"],
            path=record["object_path"],
        )

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
            record.get("bucket") != RAW_EXTRACTION_BUCKET
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
            record.get("bucket") != RAW_EXTRACTION_BUCKET
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
