"""Standalone Playwright layout inspection proof-of-concept script for Phase 6."""

import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.cv_document_v2 import CVDocumentV2, CVIdentity
from app.services.cv_render_ledger import build_cv_render_ledger
from app.services.cv_render_validation import validate_render_output
from app.services.cv_template_render_service import render_cv_document

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("poc_playwright_layout")


async def run_poc() -> None:
    _logger.info("--- Phase 6 Playwright Layout Inspection PoC ---")
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Nguyen Van A",
            headline="Senior Full Stack Software Engineer",
            email="nguyenvana@example.com",
            phone="+84 901 234 567",
        )
    )

    result = render_cv_document(doc, template_id="classic_ats")
    _logger.info("Render Hash: %s...", result.render_hash[:16])
    _logger.info("Static Validation valid: %s", result.diagnostics.is_valid)

    ledger = build_cv_render_ledger(doc)
    try:
        await validate_render_output(
            doc, result.html, ledger, result.diagnostics, run_playwright=True
        )
        _logger.info("Playwright Layout Gate Passed cleanly!")
    except Exception as exc:
        _logger.info("Playwright Layout Gate Result: %s", exc)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_poc())
