import logging
from uuid import UUID

from app.core.db import Database

logger = logging.getLogger(__name__)


class FileRepository:
    """Repository handling database persistence for files table."""

    async def create_file(
        self,
        user_id: str | UUID,
        bucket: str,
        object_path: str,
        original_filename: str,
        content_type: str,
    ) -> dict:
        """Insert a file metadata record into the database."""
        query = """
            INSERT INTO public.files (
                user_id,
                bucket,
                object_path,
                original_filename,
                content_type
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, user_id, bucket, object_path, original_filename, content_type, created_at, updated_at
        """
        row = await Database.fetch_one(
            query,
            UUID(str(user_id)) if isinstance(user_id, str) else user_id,
            bucket,
            object_path,
            original_filename,
            content_type,
        )
        return dict(row) if row else {}

    async def get_file_by_id(self, file_id: str | UUID) -> dict | None:
        """Retrieve file metadata record by ID."""
        query = """
            SELECT id, user_id, bucket, object_path, original_filename, content_type, created_at, updated_at
            FROM public.files
            WHERE id = $1
        """
        row = await Database.fetch_one(
            query,
            UUID(str(file_id)) if isinstance(file_id, str) else file_id,
        )
        return dict(row) if row else None

    async def get_file_by_path(self, bucket: str, object_path: str) -> dict | None:
        """Retrieve file metadata record by bucket and object path."""
        query = """
            SELECT id, user_id, bucket, object_path, original_filename, content_type, created_at, updated_at
            FROM public.files
            WHERE bucket = $1 AND object_path = $2
        """
        row = await Database.fetch_one(query, bucket, object_path)
        return dict(row) if row else None

    async def list_user_files(self, user_id: str | UUID) -> list[dict]:
        """List all files uploaded by a specific user."""
        query = """
            SELECT id, user_id, bucket, object_path, original_filename, content_type, created_at, updated_at
            FROM public.files
            WHERE user_id = $1
            ORDER BY created_at DESC
        """
        rows = await Database.fetch_all(
            query,
            UUID(str(user_id)) if isinstance(user_id, str) else user_id,
        )
        return [dict(r) for r in rows] if rows else []

    async def delete_file(self, file_id: str | UUID) -> bool:
        """Delete a file metadata record from database by ID."""
        query = "DELETE FROM public.files WHERE id = $1"
        res = await Database.execute(
            query,
            UUID(str(file_id)) if isinstance(file_id, str) else file_id,
        )
        # asyncpg execute returns e.g. "DELETE 1"
        return res and "DELETE 1" in res
