"""Run all database migrations in backend/migrations against the database."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public.app_schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
        )

        rows = await conn.fetch("SELECT filename FROM public.app_schema_migrations;")
        applied = {r["filename"] for r in rows}

        pending = [f for f in sql_files if f.name not in applied]
        if not pending:
            logger.info("Database schema is up to date (no pending migrations).")
            return

        for sql_file in pending:
            logger.info(f"Applying migration: {sql_file.name}")
            sql_content = sql_file.read_text(encoding="utf-8")
            async with conn.transaction():
                await conn.execute(sql_content)
                await conn.execute(
                    "INSERT INTO public.app_schema_migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING;",
                    sql_file.name,
                )
            logger.info(f"Successfully applied {sql_file.name}")

    logger.info("All pending migrations completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
