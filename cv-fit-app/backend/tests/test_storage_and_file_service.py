import uuid
from unittest.mock import AsyncMock

import pytest

from app.repositories.files import FileRepository
from app.services.files import FileService
from app.storage.base import Storage
from app.storage.supabase import SupabaseStorage


class DummyStorage:
    """Mock storage provider for testing provider portability."""

    def __init__(self):
        self.uploaded = []
        self.deleted = []

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
    ) -> str:
        self.uploaded.append((bucket, path, data, content_type))
        return path

    async def delete(
        self,
        bucket: str,
        path: str,
    ) -> None:
        self.deleted.append((bucket, path))

    async def get_url(
        self,
        bucket: str,
        path: str,
    ) -> str:
        return f"https://mock-storage.test/{bucket}/{path}"


def test_storage_protocol_compliance():
    """Verify SupabaseStorage and DummyStorage satisfy Storage protocol."""

    def check_protocol(s: Storage):
        pass

    check_protocol(SupabaseStorage())
    check_protocol(DummyStorage())


@pytest.mark.asyncio
async def test_supabase_storage_urls():
    """Test SupabaseStorage URL generation."""
    storage = SupabaseStorage(
        supabase_url="https://test.supabase.co", supabase_key="test-key"
    )
    url = await storage.get_url("user-files", "user123/cv.pdf")
    assert (
        url
        == "https://test.supabase.co/storage/v1/object/public/user-files/user123/cv.pdf"
    )
    await storage.close()


@pytest.mark.asyncio
async def test_file_service_upload():
    """Test FileService uploads via Storage and persists record in FileRepository."""
    mock_storage = DummyStorage()
    mock_repo = AsyncMock(spec=FileRepository)

    test_file_id = uuid.uuid4()
    user_id = str(uuid.uuid4())

    mock_repo.create_file.return_value = {
        "id": test_file_id,
        "user_id": user_id,
        "bucket": "user-files",
        "object_path": f"{user_id}/resume.pdf",
        "original_filename": "resume.pdf",
        "content_type": "application/pdf",
    }

    service = FileService(storage=mock_storage, repository=mock_repo)

    result = await service.upload_file(
        user_id=user_id,
        filename="resume.pdf",
        data=b"%PDF-test-data",
        content_type="application/pdf",
    )

    # 1. Assert storage upload was called with proper path and bucket
    assert len(mock_storage.uploaded) == 1
    bucket, path, data, content_type = mock_storage.uploaded[0]
    assert bucket == "user-files"
    assert path == f"{user_id}/resume.pdf"
    assert data == b"%PDF-test-data"
    assert content_type == "application/pdf"

    # 2. Assert DB repository received correct parameters
    mock_repo.create_file.assert_called_once_with(
        user_id=user_id,
        bucket="user-files",
        object_path=f"{user_id}/resume.pdf",
        original_filename="resume.pdf",
        content_type="application/pdf",
    )

    # 3. Assert returned object contains metadata and neutral generated URL
    assert result["id"] == test_file_id
    assert result["url"] == f"https://mock-storage.test/user-files/{user_id}/resume.pdf"


@pytest.mark.asyncio
async def test_file_service_delete():
    """Test FileService delete file flow."""
    mock_storage = DummyStorage()
    mock_repo = AsyncMock(spec=FileRepository)

    file_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    mock_repo.get_file_by_id.return_value = {
        "id": file_id,
        "user_id": user_id,
        "bucket": "user-files",
        "object_path": f"{user_id}/resume.pdf",
    }
    mock_repo.delete_file.return_value = True

    service = FileService(storage=mock_storage, repository=mock_repo)

    deleted = await service.delete_file(user_id=user_id, file_id=file_id)

    assert deleted is True
    assert len(mock_storage.deleted) == 1
    assert mock_storage.deleted[0] == ("user-files", f"{user_id}/resume.pdf")
    mock_repo.delete_file.assert_called_once_with(file_id)


@pytest.mark.asyncio
async def test_file_service_upload_with_custom_original_filename():
    """Test FileService preserves separate original_filename and storage filename."""
    mock_storage = DummyStorage()
    mock_repo = AsyncMock(spec=FileRepository)

    test_file_id = uuid.uuid4()
    user_id = str(uuid.uuid4())
    stored_filename = "20260818_013227_my_cv.pdf"
    original_filename = "my_cv.pdf"

    mock_repo.create_file.return_value = {
        "id": test_file_id,
        "user_id": user_id,
        "bucket": "cv",
        "object_path": f"{user_id}/{stored_filename}",
        "original_filename": original_filename,
        "content_type": "application/pdf",
    }

    service = FileService(storage=mock_storage, repository=mock_repo)

    result = await service.upload_file(
        user_id=user_id,
        filename=stored_filename,
        data=b"%PDF-test-data",
        content_type="application/pdf",
        bucket="cv",
        original_filename=original_filename,
    )

    assert len(mock_storage.uploaded) == 1
    bucket, path, data, content_type = mock_storage.uploaded[0]
    assert bucket == "cv"
    assert path == f"{user_id}/{stored_filename}"

    mock_repo.create_file.assert_called_once_with(
        user_id=user_id,
        bucket="cv",
        object_path=f"{user_id}/{stored_filename}",
        original_filename=original_filename,
        content_type="application/pdf",
    )

    assert result["id"] == test_file_id
    assert result["original_filename"] == original_filename
