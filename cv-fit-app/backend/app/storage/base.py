from typing import Protocol


class Storage(Protocol):
    """Abstract storage interface defining object storage operations."""

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload data to object storage at specified bucket and path.

        Returns the storage path or identifier.
        """
        ...

    async def delete(
        self,
        bucket: str,
        path: str,
    ) -> None:
        """Delete an object from specified bucket and path."""
        ...

    async def get_url(
        self,
        bucket: str,
        path: str,
    ) -> str:
        """Get public or accessible URL for an object in specified bucket and path."""
        ...
