import logging

import asyncpg

from app.core.config import DATABASE_URL

logger = logging.getLogger(__name__)


class Database:
    pool: asyncpg.Pool = None

    @classmethod
    async def connect(cls):
        if not cls.pool:
            try:
                # Create connection pool
                cls.pool = await asyncpg.create_pool(
                    DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    timeout=30.0,
                    statement_cache_size=0,
                    max_inactive_connection_lifetime=300.0,
                )
                logger.info("Successfully connected to PostgreSQL database pool.")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL database: {e}")
                raise e

    @classmethod
    async def disconnect(cls):
        if cls.pool:
            await cls.pool.close()
            cls.pool = None
            logger.info("Closed PostgreSQL database pool.")

    @classmethod
    async def fetch_one(cls, query: str, *args):
        if not cls.pool:
            await cls.connect()
        async with cls.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    @classmethod
    async def fetch_all(cls, query: str, *args):
        if not cls.pool:
            await cls.connect()
        async with cls.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    @classmethod
    async def execute(cls, query: str, *args):
        if not cls.pool:
            await cls.connect()
        async with cls.pool.acquire() as conn:
            return await conn.execute(query, *args)
