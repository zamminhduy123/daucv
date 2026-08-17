import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from app.core.db import Database
from app.schemas.user import CVResponse, UserProfileResponse

logger = logging.getLogger(__name__)


async def get_profile_with_stats(user: dict) -> UserProfileResponse:
    user_id = user["id"]

    # Concurrent fetch of active CV and total CV count
    active_cv_task = Database.fetch_one(
        "SELECT id, cv_filename, cv_text, is_active, created_at FROM public.user_cvs WHERE user_id = $1 AND is_active = TRUE LIMIT 1",
        user_id,
    )
    count_task = Database.fetch_one(
        "SELECT COUNT(*) as total FROM public.user_cvs WHERE user_id = $1",
        user_id,
    )

    active_cv_row, count_row = await asyncio.gather(active_cv_task, count_task)

    active_cv = None
    active_cv_age_days = None

    if active_cv_row:
        active_cv = CVResponse.model_validate(dict(active_cv_row))
        created_at = active_cv_row.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            active_cv_age_days = max(0, (now - created_at).days)

    total_cvs = count_row["total"] if count_row else 0

    return UserProfileResponse(
        id=user_id,
        email=user["email"],
        name=user["name"],
        image=user["image"],
        credits=user["credits"],
        active_cv=active_cv,
        total_cvs=total_cvs,
        active_cv_age_days=active_cv_age_days,
    )


async def list_cvs(user_id: UUID) -> list[CVResponse]:
    rows = await Database.fetch_all(
        "SELECT id, cv_filename, cv_text, is_active, created_at FROM public.user_cvs WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    return [CVResponse.model_validate(dict(r)) for r in rows]


async def create_cv(user_id: UUID, cv_text: str, cv_filename: str) -> CVResponse:
    if not Database.pool:
        await Database.connect()

    async with Database.pool.acquire() as conn, conn.transaction():
        # Lock the user's row to prevent concurrent race conditions
        user = await conn.fetchrow(
            "SELECT credits FROM public.users WHERE id = $1 FOR UPDATE",
            user_id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

        # Deactivate previous active CVs
        await conn.execute(
            "UPDATE public.user_cvs SET is_active = FALSE WHERE user_id = $1",
            user_id,
        )

        # Insert the new active CV
        row = await conn.fetchrow(
            "INSERT INTO public.user_cvs (user_id, cv_text, cv_filename, is_active) VALUES ($1, $2, $3, TRUE) RETURNING id, cv_filename, cv_text, is_active, created_at",
            user_id,
            cv_text,
            cv_filename,
        )

    return CVResponse.model_validate(dict(row))


async def update_active_cv_text(
    user_id: UUID,
    cv_text: str,
    cv_filename: str,
) -> CVResponse:
    if not Database.pool:
        await Database.connect()

    async with Database.pool.acquire() as conn, conn.transaction():
        # Lock user row to serialize updates
        user = await conn.fetchrow(
            "SELECT credits FROM public.users WHERE id = $1 FOR UPDATE",
            user_id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

        # Check if active CV exists
        active = await conn.fetchrow(
            "SELECT id FROM public.user_cvs WHERE user_id = $1 AND is_active = TRUE LIMIT 1",
            user_id,
        )

        if active:
            # Update existing active CV in place
            row = await conn.fetchrow(
                "UPDATE public.user_cvs SET cv_text = $1, cv_filename = $2 WHERE id = $3 RETURNING id, cv_filename, cv_text, is_active, created_at",
                cv_text,
                cv_filename,
                active["id"],
            )
        else:
            # Create a new active CV if none exists
            row = await conn.fetchrow(
                "INSERT INTO public.user_cvs (user_id, cv_text, cv_filename, is_active) VALUES ($1, $2, $3, TRUE) RETURNING id, cv_filename, cv_text, is_active, created_at",
                user_id,
                cv_text,
                cv_filename,
            )

    return CVResponse.model_validate(dict(row))


async def deactivate_cv(cv_id: UUID, user_id: UUID) -> bool:
    updated = await Database.execute(
        "UPDATE public.user_cvs SET is_active = FALSE WHERE id = $1 AND user_id = $2",
        cv_id,
        user_id,
    )
    if updated == "UPDATE 0":
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV hoặc bạn không có quyền sửa đổi CV này.",
        )
    return True


async def submit_user_feedback(
    user_id: UUID,
    name: str | None,
    avatar: str | None,
    rating: int,
    content: str,
) -> tuple[int, int]:
    """Submits user feedback and rewards +5 credits on the first submission.
    Returns (credits_rewarded, new_credits_balance).
    """
    if not Database.pool:
        await Database.connect()

    async with Database.pool.acquire() as conn, conn.transaction():
        # Get user info and lock to serialize
        user = await conn.fetchrow(
            "SELECT credits FROM public.users WHERE id = $1 FOR UPDATE",
            user_id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

        # Check if user has already submitted feedback before
        existing_feedback = await conn.fetchrow(
            "SELECT id FROM public.feedbacks WHERE user_id = $1 LIMIT 1",
            user_id,
        )

        credits_rewarded = 0
        new_balance = user["credits"]

        if not existing_feedback:
            credits_rewarded = 5
            new_balance = user["credits"] + credits_rewarded

            # Update user credits
            await conn.execute(
                "UPDATE public.users SET credits = $1 WHERE id = $2",
                new_balance,
                user_id,
            )

            # Log transaction
            await conn.execute(
                "INSERT INTO public.credit_transactions (user_id, amount, type, description) VALUES ($1, $2, $3, $4)",
                user_id,
                credits_rewarded,
                "feedback_bonus",
                "Thưởng 5 credits khi gửi đánh giá phản hồi đầu tiên.",
            )

        # Insert feedback record (defaulting to TRUE for immediate visibility)
        await conn.execute(
            """
            INSERT INTO public.feedbacks (user_id, name, avatar, rating, content, is_public)
            VALUES ($1, $2, $3, $4, $5, TRUE)
            """,
            user_id,
            name,
            avatar,
            rating,
            content,
        )

    return credits_rewarded, new_balance
