import logging

from app.core.db import Database

_logger = logging.getLogger(__name__)


async def get_file(bucket_name: str):
    db = Database()
    return await db.execute(
        "SELECT * FROM files WHERE bucket_name = %s", (bucket_name,)
    )


async def upload_file(bucket_name: str, file_data: bytes):
    db = Database()
    return await db.execute(
        "SELECT * FROM files WHERE bucket_name = %s", (bucket_name,)
    )
