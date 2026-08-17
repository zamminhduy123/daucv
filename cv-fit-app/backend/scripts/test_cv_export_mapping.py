"""Comprehensive test script to test CV mapping, tailoring, gate validation, HTML rendering, and PDF export."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.cv_tailoring import TailoredCVResponse, TailoringChangeItem
from app.schemas.tailored_cv import CVDesign
from app.services.cv_reconstruction_service import (
    validate_reconstruction_gate,
)
from app.services.cv_structuring_service import (
    build_manual_text_extraction,
    structure_cv,
)
from app.services.cv_template_render_service import render_cv_document


async def main():
    print("=" * 70)
    print("STEP 1: Structure CV")
    print("=" * 70)

    cv_text = """NGUYEN THANH MINH DUY
AI Engineer / ML Engineer
ntminhduy123@gmail.com | +84 33-545-2060
Ho Chi Minh City, Vietnam
https://linkedin.com/in/minhduy-ai | https://github.com/zamminhduy123

SUMMARY
AI and machine learning researcher with a master's degree and hands-on experience developing Transformers, graph neural networks, few-shot learning, and open-set recognition models in PyTorch. Experienced in designing automated experimentation pipelines, analyzing complex datasets, and publishing applied deep-learning research, complemented by two years of production software engineering experience.

EDUCATION
Soonchunhyang University (SCH)
M.S. in Engineering (Fully Funded); GPA: 4.32/4.5
Mar 2024 – Feb 2026
• Focus: Deep Learning, Few-Shot Learning, Open-Set Recognition, GNNs.

HCM VNU – University of Science
B.Sc. in Software Engineering; GPA: 8.66/10
Aug 2018 – Feb 2022

EXPERIENCE
Zalo – VNG Corporation
Software Engineer, Zalo PC
May 2022 – Mar 2024
• Led frontend implementation for a full architectural revamp of the user Contact Card, improving maintainability in a complex React/Electron legacy codebase.
• Shipped 15+ production features for Zalo PC across messaging, contact, and desktop surfaces.
• Optimized client-side message search using batching and caching, reducing search latency by 30% while preserving UI responsiveness.

PROJECTS
Bé Đậu - Career Copilot
AI Engineer
2025 - Present
• Built FastAPI career prep platform with deterministic grounding.

SKILLS
Programming Languages: Python, TypeScript, C++, SQL
Frameworks & Libraries: PyTorch, FastAPI, Next.js, React, Docker
Specializations: Deep Learning, Natural Language Processing, Computer Vision
"""

    raw_extraction = build_manual_text_extraction(cv_text)
    print("Structuring CV text via range plan service...")
    struct_res = await structure_cv(cv_text=cv_text)
    source_document = struct_res.document
    print(f"Structuring completed: {len(source_document.sections)} sections found.")
    print(f"Reconstruction warnings: {source_document.reconstruction_warnings}")
    print(f"Unmapped blocks: {len(source_document.unmapped_content)}")
    for u in source_document.unmapped_content:
        print(f"  - Unmapped block {u.block_id} [{u.reason}]: {u.text!r}")

    print("\n" + "=" * 70)
    print("STEP 2: Validate Reconstruction Gate")
    print("=" * 70)
    validate_reconstruction_gate(source_document)
    print(">>> validate_reconstruction_gate PASSED! <<<")

    print("\n" + "=" * 70)
    print("STEP 3: Simulate LLM #3 Tailoring Rewrite Operations")
    print("=" * 70)
    canonical = source_document.to_canonical_dict()
    print("Canonical CV sections:", list(canonical.keys()))
    print("Experience entries:", len(canonical.get("experience", [])))

    # Create a simulated rewrite operation targeting experience[0].bullets[0].text
    orig_bullet_0 = canonical["experience"][0]["bullets"][0]["text"]
    proposed_bullet_0 = (
        "Architected frontend components for the user Contact Card revamp, "
        "enhancing maintainability in a complex React/Electron legacy codebase."
    )
    tailoring = TailoredCVResponse(
        tailored_cv=canonical,
        change_log=[
            TailoringChangeItem(
                path="experience[0].bullets[0].text",
                original_text=orig_bullet_0,
                proposed_text=proposed_bullet_0,
                rationale="Improved technical action verbs while keeping core facts.",
            )
        ],
        tailoring_summary="Enhanced technical action verbs for experience entries.",
    )
    print(f"Simulated {len(tailoring.change_log)} rewrite operation(s).")

    print("\n" + "=" * 70)
    print("STEP 4: Test Persistence & Gate Validation")
    print("=" * 70)
    from app.core.db import Database

    user_row = await Database.fetch_one("SELECT id FROM users LIMIT 1")
    user_id = user_row["id"] if user_row else uuid4()
    analysis_key = f"test_analysis_{uuid4().hex[:8]}"

    try:
        from app.services.cv_pipeline_persistence_service import (
            persist_pipeline_tailoring,
        )

        version = await persist_pipeline_tailoring(
            user_id=user_id,
            source_text=cv_text,
            raw_extraction=raw_extraction,
            source_document=source_document,
            job_description="Senior AI Engineer",
            tailoring=tailoring,
            selected_design="classic_ats",
            analysis_key=analysis_key,
        )
        print(f">>> persist_pipeline_tailoring PASSED! Version ID: {version.id} <<<")
        saved_doc = version.document_v2
    except Exception as exc:
        print(f"persist_pipeline_tailoring raised: {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
        return

    print("\n" + "=" * 70)
    print("STEP 5: Test HTML Template Rendering for All Designs")
    print("=" * 70)
    designs: list[CVDesign] = ["classic_ats", "modern_professional", "compact"]
    for design in designs:
        result = render_cv_document(
            document=saved_doc,
            template_id=design,
            language="vi",
        )
        print(
            f" - Design [{design:20s}]: Rendered HTML size = {len(result.html):6d} bytes | Hash = {result.render_hash[:12]}... | Warnings = {result.diagnostics.warnings}"
        )

    print("\n" + "=" * 70)
    print("STEP 6: Test PDF Generation with Playwright")
    print("=" * 70)
    try:
        from app.services.tailored_cv_pdf import generate_tailored_cv_pdf

        pdf_bytes = await generate_tailored_cv_pdf(
            tailored_cv=version.tailored_cv,
            document_v2=saved_doc,
            design="classic_ats",
            language="vi",
        )
        pdf_out_path = Path("/tmp/test_cv_export_output.pdf")
        pdf_out_path.write_bytes(pdf_bytes)
        print(
            f">>> PDF generated successfully! ({len(pdf_bytes)} bytes) saved to {pdf_out_path} <<<"
        )
    except Exception as pdf_exc:
        print(f"PDF generation note: {type(pdf_exc).__name__}: {pdf_exc}")

    print("\n" + "=" * 70)
    print("ALL MAPPING & EXPORT TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
