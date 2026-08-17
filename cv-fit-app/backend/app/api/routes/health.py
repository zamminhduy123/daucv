"""Health-check probes for production readiness (Phase 8)."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services import health_service

router = APIRouter()


@router.get("/health/live")
async def liveness_probe() -> dict[str, str]:
    """Cheap, unblocked liveness probe."""
    return await health_service.check_liveness()


@router.get("/health/ready")
async def readiness_probe() -> dict[str, Any]:
    """Bounded readiness probe checking DB, storage, font assets, and Playwright binary path."""
    res = await health_service.check_readiness()
    if res.get("status") != "ok":
        raise HTTPException(status_code=503, detail=res)
    return res


@router.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "CVFit API is running"}
