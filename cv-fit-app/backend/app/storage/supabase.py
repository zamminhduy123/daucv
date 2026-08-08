import logging
from urllib.parse import quote

import httpx

from app.core.config import SUPABASE_KEY, SUPABASE_URL
from app.storage.base import Storage

logger = logging.getLogger(__name__)


class SupabaseStorage(Storage):
    """Supabase REST API object storage implementation."""

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        base_url = (supabase_url or SUPABASE_URL or "").rstrip("/")
        for suffix in ("/storage/v1/object", "/storage/v1", "/storage"):
            if base_url.endswith(suffix):
                base_url = base_url[:-len(suffix)].rstrip("/")
        self.supabase_url = base_url
        self.supabase_key = supabase_key or SUPABASE_KEY or ""
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
            self._owns_client = True
        return self._client

    async def close(self) -> None:
        """Close client if managed internally."""
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
        upsert: bool = True,
    ) -> str:
        client = await self._get_client()
        bucket_encoded = quote(bucket, safe="")
        path_encoded = quote(path, safe="/")

        url = f"{self.supabase_url}/storage/v1/object/{bucket_encoded}/{path_encoded}"

        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": content_type,
            "x-upsert": str(upsert).lower(),
        }
        
        logger.info(f"Uploading file to Supabase: {path} -> {url}")

        response = await client.post(url, content=data, headers=headers)
        if response.is_error:
            logger.error(
                f"Supabase upload error [{response.status_code}]: {response.text}"
            )
            raise RuntimeError(
                f"Supabase upload failed ({response.status_code}): {response.text}"
            )

        return path


    async def delete(
        self,
        bucket: str,
        path: str,
    ) -> None:
        client = await self._get_client()
        bucket_encoded = quote(bucket, safe="")

        url = f"{self.supabase_url}/storage/v1/object/{bucket_encoded}"

        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
        }

        response = await client.request(
            "DELETE",
            url,
            json={"prefixes": [path]},
            headers=headers,
        )
        response.raise_for_status()

    async def get_url(
        self,
        bucket: str,
        path: str,
    ) -> str:
        bucket_encoded = quote(bucket, safe="")
        path_encoded = quote(path, safe="/")
        return f"{self.supabase_url}/storage/v1/object/public/{bucket_encoded}/{path_encoded}"
