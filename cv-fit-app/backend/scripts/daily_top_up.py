#!/usr/bin/env python3
"""
Daily Top-up Script for DauCV.

This script updates all users by adding 5 credits and records a corresponding transaction
in the credit_transactions table. It can be run as a daily cron job.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("daily_top_up")

from app.core.db import Database  # noqa: E402


async def run_daily_top_up() -> int:
    """
    Transactionally adds 5 credits to all users and inserts a ledger entry.
    Returns the number of users topped up.
    """
    logger.info("Connecting to the database...")
    await Database.connect()

    try:
        async with Database.pool.acquire() as conn, conn.transaction():
            # Get user count
            users = await conn.fetch("SELECT id FROM public.users")
            user_ids = [user["id"] for user in users]
            users_count = len(user_ids)

            logger.info(f"Found {users_count} users to top up.")
            if users_count == 0:
                logger.info("No users found in the database. Exiting.")
                return 0

            # 1. Update credits for all users
            await conn.execute(
                "UPDATE public.users SET credits = credits + 5, updated_at = now()"
            )

            # 2. Insert transaction ledger entries for all users
            await conn.execute(
                """
                INSERT INTO public.credit_transactions (user_id, amount, type, description)
                SELECT id, 5, 'daily_bonus', 'Tặng 5 credits hàng ngày.' FROM public.users
                """
            )

            logger.info(f"Successfully credited +5 to all {users_count} users.")
            return users_count

    except Exception as e:
        logger.error(f"Error during daily top-up: {e}")
        raise e
    finally:
        logger.info("Disconnecting from the database...")
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(run_daily_top_up())
