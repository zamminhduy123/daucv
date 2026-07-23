"""Run all database migrations in backend/migrations against the database."""

import asyncio
import logging
from pathlib import Path

from app.core.db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_migrations")


async def run_migrations():
    logger.info("Connecting to database...")
    await Database.connect()

    migrations_dir = Path(__file__).parent.parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        logger.warning(f"No SQL migration files found in {migrations_dir}")
        return

    async with Database.pool.acquire() as conn:
        for sql_file in sql_files:
            logger.info(f"Applying migration: {sql_file.name}")
            sql_content = sql_file.read_text(encoding="utf-8")
            await conn.execute(sql_content)
            logger.info(f"Successfully applied {sql_file.name}")

    logger.info("All migrations completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
