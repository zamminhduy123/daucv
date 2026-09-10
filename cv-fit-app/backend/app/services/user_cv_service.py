import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from app.core.db import Database
from app.models.cv_document_v2 import CVDocumentV2
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
    try:
        rows = await Database.fetch_all(
            "SELECT id, cv_filename, cv_text, is_active, created_at, raw_extraction_ref, pdf_file_id FROM public.user_cvs WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )
    except Exception as exc:
        # Migration 010/011 may not have applied yet on some
        # environments. Fall back to the legacy column set so the CV list
        # keeps working instead of 500ing the picker.
        if "raw_extraction_ref" not in str(exc) and "pdf_file_id" not in str(exc):
            raise
        logger.warning(
            "user_cvs PDF/raw columns missing; listing without them. "
            "Apply migrations 010 and 011.",
            exc_info=True,
        )
        rows = await Database.fetch_all(
            "SELECT id, cv_filename, cv_text, is_active, created_at FROM public.user_cvs WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )
        return [
            CVResponse.model_validate(
                {**dict(r), "raw_extraction_ref": None, "pdf_file_id": None}
            )
            for r in rows
        ]
    return [CVResponse.model_validate(dict(r)) for r in rows]


async def get_cv(cv_id: UUID, user_id: UUID) -> CVResponse | None:
    """Fetch one source CV row (ownership-checked) or None."""
    try:
        row = await Database.fetch_one(
            "SELECT id, cv_filename, cv_text, is_active, created_at, raw_extraction_ref, pdf_file_id FROM public.user_cvs WHERE id = $1 AND user_id = $2",
            cv_id,
            user_id,
        )
    except Exception as exc:
        if "raw_extraction_ref" not in str(exc) and "pdf_file_id" not in str(exc):
            raise
        row = await Database.fetch_one(
            "SELECT id, cv_filename, cv_text, is_active, created_at FROM public.user_cvs WHERE id = $1 AND user_id = $2",
            cv_id,
            user_id,
        )
        if row is None:
            return None
        return CVResponse.model_validate(
            {**dict(row), "raw_extraction_ref": None, "pdf_file_id": None}
        )
    if row is None:
        return None
    return CVResponse.model_validate(dict(row))


MAX_CVS_PER_USER = 10


async def create_cv(
    user_id: UUID,
    cv_text: str,
    cv_filename: str,
    raw_extraction_ref: str | None = None,
    pdf_file_id: str | None = None,
) -> CVResponse:
    """Store a new source CV row alongside existing rows (multi-CV switcher).

    New rows are inactive plain rows; selection is client-side. The legacy
    active row (if any) is left untouched so old clients keep working.
    """
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

        # Cap stored CVs so the picker stays usable; users delete one to add.
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM public.user_cvs WHERE user_id = $1",
            user_id,
        )
        if existing is not None and int(existing) >= MAX_CVS_PER_USER:
            raise HTTPException(
                status_code=409,
                detail=f"Bạn đã đạt giới hạn {MAX_CVS_PER_USER} CV. Hãy xóa một CV cũ để thêm CV mới.",
            )

        # Extra-slot rule (edit-stage flow): the first CV slot is free; each
        # additional CV row costs 1 credit once at creation. Edits/saves stay
        # free. Deleting frees the slot without refund.
        existing_count = int(existing or 0)
        if existing_count >= 1:
            balance = int(user["credits"] or 0)
            if balance < 1:
                raise HTTPException(
                    status_code=402,
                    detail="Hết credit — cần 1 credit để mở khóa CV mới. Hãy nạp thêm.",
                )
            await conn.execute(
                "UPDATE public.users SET credits = credits - 1 WHERE id = $1",
                user_id,
            )
            await conn.execute(
                "INSERT INTO public.credit_transactions (user_id, amount, type, description) VALUES ($1, $2, $3, $4)",
                user_id,
                -1,
                "extra_cv_slot",
                "Mở khóa slot CV mới",
            )

        # Insert the new CV without touching other rows (coexist, not replace)
        row = await conn.fetchrow(
            "INSERT INTO public.user_cvs (user_id, cv_text, cv_filename, is_active, raw_extraction_ref, pdf_file_id) VALUES ($1, $2, $3, FALSE, $4, $5) RETURNING id, cv_filename, cv_text, is_active, created_at, raw_extraction_ref, pdf_file_id",
            user_id,
            cv_text,
            cv_filename,
            raw_extraction_ref,
            pdf_file_id,
        )

    return CVResponse.model_validate(dict(row))


async def update_cv_text(
    cv_id: UUID,
    user_id: UUID,
    cv_text: str,
    cv_filename: str,
    raw_extraction_ref: str | None = None,
) -> CVResponse:
    """Update one source CV row by id (ownership-checked)."""
    if not Database.pool:
        await Database.connect()

    async with Database.pool.acquire() as conn, conn.transaction():
        user = await conn.fetchrow(
            "SELECT credits FROM public.users WHERE id = $1 FOR UPDATE",
            user_id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

        row = await conn.fetchrow(
            "UPDATE public.user_cvs SET cv_text = $1, cv_filename = $2, raw_extraction_ref = COALESCE($3, raw_extraction_ref) WHERE id = $4 AND user_id = $5 RETURNING id, cv_filename, cv_text, is_active, created_at, raw_extraction_ref, pdf_file_id",
            cv_text,
            cv_filename,
            raw_extraction_ref,
            cv_id,
            user_id,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy CV hoặc bạn không có quyền sửa đổi CV này.",
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


async def delete_cv(cv_id: UUID, user_id: UUID) -> bool:
    """Hard-delete one source CV row (ownership-checked).

    Linked tailored versions survive via ON DELETE SET NULL. Associated raw
    extraction files are cleaned up by the caller (best-effort, idempotent).
    """
    updated = await Database.execute(
        "DELETE FROM public.user_cvs WHERE id = $1 AND user_id = $2",
        cv_id,
        user_id,
    )
    if updated == "DELETE 0":
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV hoặc bạn không có quyền sửa đổi CV này.",
        )
    return True


async def deactivate_cv(cv_id: UUID, user_id: UUID) -> bool:
    """Legacy deactivate path (kept for old clients); prefer delete_cv."""
    return await delete_cv(cv_id, user_id)


async def save_structured_document(
    cv_id: UUID, user_id: UUID, document_json: str
) -> str:
    """Persist the wizard-edited structured CV JSON (ownership-checked).

    Returns the update timestamp ISO string. Validates JSON shape lightly;
    full CVDocumentV2 validation happens at the route layer.
    """
    import json as _json

    try:
        parsed = _json.loads(document_json)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422, detail="Structured document không phải JSON hợp lệ."
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=422, detail="Structured document phải là một object."
        )
    if not Database.pool:
        await Database.connect()
    row = await Database.fetch_one(
        "UPDATE public.user_cvs SET structured_document = $1::jsonb, structured_updated_at = now() WHERE id = $2 AND user_id = $3 RETURNING structured_updated_at",
        document_json,
        cv_id,
        user_id,
    )
    if not row or not row["structured_updated_at"]:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV hoặc bạn không có quyền sửa đổi CV này.",
        )
    updated_at = row["structured_updated_at"]
    return (
        updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at)
    )


async def get_structured_document(cv_id: UUID, user_id: UUID) -> dict | None:
    """Return the saved wizard JSON for one CV row, or None if never saved."""
    if not Database.pool:
        await Database.connect()
    row = await Database.fetch_one(
        "SELECT structured_document FROM public.user_cvs WHERE id = $1 AND user_id = $2",
        cv_id,
        user_id,
    )
    if not row or row["structured_document"] is None:
        return None
    value = row["structured_document"]
    if isinstance(value, dict):
        return value
    import json as _json

    try:
        return _json.loads(value)
    except (ValueError, TypeError):
        return None


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


def mark_user_edited(document: CVDocumentV2) -> CVDocumentV2:
    """Preserve per-brick provenance for wizard-saved documents.

    The review wizard stamps only touched bricks with ``origin == USER_EDIT``
    (frontend ``applyBlockPatch``). Untouched bricks keep the extractor's
    ``EXTRACTED`` origin. This function therefore never blanket-overwrites:
    it only backfills a missing origin so downstream validators always see
    an explicit author. ``source_block_ids``/``source_line_ids`` are untouched.
    """
    from app.models.cv_document_v2 import (
        ContentOrigin,
    )

    for section in document.sections:
        for block in section.blocks:
            if not getattr(block, "origin", None):
                block.origin = ContentOrigin.EXTRACTED
    if document.summary is not None and not getattr(document.summary, "origin", None):
        document.summary.origin = ContentOrigin.EXTRACTED
    return document


async def _mark_user_edited(document: CVDocumentV2) -> CVDocumentV2:
    """Deprecated alias: prefer :func:`mark_user_edited` (sync)."""
    return mark_user_edited(document)
