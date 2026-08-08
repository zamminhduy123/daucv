import logging
from typing import Any

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

        # 2. Store neutral metadata in database
        record = await self.repository.create_file(
            user_id=user_id,
            bucket=bucket,
            object_path=path,
            original_filename=filename,
            content_type=content_type,
        )

        # 3. Generate dynamic URL from current storage provider
        url = await self.storage.get_url(bucket=bucket, path=path)

        return {
            **record,
            "url": url,
        }

    async def get_file_url(self, file_id: str) -> str | None:
        """Get accessible URL for a stored file by ID."""
        record = await self.repository.get_file_by_id(file_id)
        if not record:
            return None
        return await self.storage.get_url(
            bucket=record["bucket"],
            path=record["object_path"],
        )

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
