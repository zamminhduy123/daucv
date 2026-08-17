"""Service layer for liveness and readiness health checks."""

import asyncio
import logging
from typing import Any

from app.core.db import Database
from app.services import cv_template_registry

_logger = logging.getLogger(__name__)


async def check_liveness() -> dict[str, str]:
    """Basic liveness check."""
    return {"status": "ok"}


async def check_readiness() -> dict[str, Any]:
    """Comprehensive readiness check covering DB, Storage, Playwright/Chromium, and Font assets."""
    readiness: dict[str, Any] = {
        "status": "ok",
        "database": "ok",
        "storage": "ok",
        "playwright": "ok",
        "fonts": "ok",
    }

    # 1. Database Check
    try:
        await Database.fetch_one("SELECT 1")
    except Exception as exc:
        _logger.error("Readiness check DB failure: %s", exc)
        readiness["database"] = f"unhealthy: {exc}"
        readiness["status"] = "unhealthy"

    # 2. Storage / Files table Check
    try:
        await Database.fetch_one("SELECT count(*) FROM public.files")
    except Exception as exc:
        _logger.warning("Readiness check storage files table failure: %s", exc)
        readiness["storage"] = f"degraded: {exc}"

    # 3. Playwright / Chromium Check
    try:
        proc = await asyncio.create_subprocess_exec(
            "npx",
            "playwright",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        if proc.returncode != 0:
            err_msg = stderr.decode().strip() or stdout.decode().strip()
            _logger.error(
                "Playwright check failed with code %d: %s", proc.returncode, err_msg
            )
            readiness["playwright"] = f"unhealthy: code {proc.returncode}"
            readiness["status"] = "unhealthy"
    except Exception as exc:
        _logger.error("Playwright readiness check failed: %s", exc)
        readiness["playwright"] = f"unhealthy: {exc}"
        readiness["status"] = "unhealthy"

    # 4. Font assets Check
    try:
        fonts_dir = cv_template_registry.FONTS_DIR
        if not fonts_dir.exists() or not any(fonts_dir.iterdir()):
            _logger.error("Font directory missing or empty: %s", fonts_dir)
            readiness["fonts"] = "unhealthy: fonts directory missing or empty"
            readiness["status"] = "unhealthy"
    except Exception as exc:
        _logger.error("Font readiness check failed: %s", exc)
        readiness["fonts"] = f"unhealthy: {exc}"
        readiness["status"] = "unhealthy"

    return readiness
