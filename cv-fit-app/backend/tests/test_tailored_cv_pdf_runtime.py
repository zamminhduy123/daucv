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

    pdf_bytes = asyncio.run(generate_tailored_cv_pdf(cv, design))
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as document:
        text = "\n".join(page.extract_text() or "" for page in document.pages)
        assert pdf_bytes.startswith(b"%PDF")
        if design == "compact_one_page":
            assert len(document.pages) == 1
        assert "Duy Nguyen" in text
        assert "EXPERIENCE" in text.upper()
        assert "Preserved experience bullet 0." in text
        assert final_item in text
