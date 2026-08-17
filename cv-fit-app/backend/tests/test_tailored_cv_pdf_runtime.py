import asyncio
import io

import pdfplumber
import pytest

from app.models.domain import TailoredCV, TailoredCVSection
from app.services.tailored_cv_pdf import generate_tailored_cv_pdf


@pytest.mark.parametrize(
    "design",
    ["classic_ats", "modern_professional", "compact_one_page"],
)
def test_pdf_designs_preserve_content(design: str) -> None:
    final_item = "Final preserved experience bullet."
    items = [f"• Preserved experience bullet {index}." for index in range(35)]
    items.append(f"• {final_item}")
    cv = TailoredCV(
        name="Duy Nguyen",
        headline="Engineer",
        contact_lines=["duy@example.com"],
        summary="Backend engineer.",
        sections=[TailoredCVSection(title="Experience", items=items)],
    )

    try:
        pdf_bytes = asyncio.run(generate_tailored_cv_pdf(cv, design))
    except Exception as exc:
        if (
            "Target closed" in str(exc)
            or "TargetClosedError" in str(type(exc).__name__)
            or "Permission denied" in str(exc)
            or "MachPort" in str(exc)
        ):
            pytest.skip(
                f"Playwright Chromium launch unavailable in sandbox environment: {exc}"
            )
        raise
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as document:
        text = "\n".join(page.extract_text() or "" for page in document.pages)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(document.pages) >= 1
        assert "Duy Nguyen".upper() in text.upper()
        assert "EXPERIENCE" in text.upper()
        assert "Preserved experience bullet 0." in text
        assert final_item in text
