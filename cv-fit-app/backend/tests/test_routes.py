"""Endpoint tests that verify route registration and input validation.

No LLM calls — these only test that routes exist, accept valid input,
and reject invalid input with 422 (Pydantic validation errors).
"""

import asyncio
import io
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_positioned_pdf(rows: list[tuple[float, float, str]]) -> bytes:
    """Build a small privacy-safe PDF with independently positioned text rows."""
    commands: list[str] = []
    for x, top, text in rows:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"BT /F1 10 Tf {x} {792 - top} Td ({escaped}) Tj ET")
    content = " ".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, pdf_object in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(pdf_object + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(pdf)


# All POST endpoints that should be registered.
# If a new route is added, append to this list.
POST_ROUTES = [
    "/api/upload-and-match",
    "/api/extract-pdf",
    "/api/analyze-cv",
    "/api/cv/parse",
    "/api/cv/evaluate",
    "/api/cv/tailor",
    "/api/writer/generate",
    "/api/interview/chat",
    "/api/interview/finish",
    "/api/interview/tts",
    "/api/jobs/parse-profile",
    "/api/jobs/search",
    "/api/user/feedback",
]


@pytest.mark.parametrize(
    "path",
    POST_ROUTES,
    ids=lambda p: p.replace("/", "_").strip("_"),
)
def test_post_route_is_registered(client: TestClient, path: str) -> None:
    """Each POST route should exist (not 404). Hit with GET; we only care about route presence."""
    resp = client.get(path)
    # 405 = route exists but wrong method; 200 = works with GET; anything else ≠ 404
    assert resp.status_code != 404, f"Route {path} is not registered (404)"


def test_analyze_cv_rejects_empty_body(client: TestClient) -> None:
    resp = client.post("/api/analyze-cv", json={})
    assert resp.status_code == 422


def test_extract_pdf_reuses_canonical_blocks_and_preserves_metadata(
    client: TestClient,
) -> None:
    from app.core.config import RAW_EXTRACTION_BUCKET
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )

    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=2,
                width=595.0,
                height=842.0,
                blocks=[
                    RawBlock(
                        block_id="p2-b1",
                        page=2,
                        text="EDUCATION",
                        bbox=(72.0, 40.0, 180.0, 52.0),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p2-b2",
                        page=2,
                        text="Soonchunhyang University",
                        bbox=(72.0, 80.0, 240.0, 96.0),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                ],
            )
        ],
    )
    persisted_raw_id = "11111111-1111-4111-8111-111111111111"
    source_pdf_id = "22222222-2222-4222-8222-222222222222"
    with (
        patch(
            "app.api.routes.user.extract_cv_content_blocks",
            return_value=raw,
        ) as extract_blocks,
        patch(
            "app.services.files.FileService.upload_file",
            new=AsyncMock(
                side_effect=[
                    {"id": persisted_raw_id},
                    {"id": source_pdf_id},
                ]
            ),
        ) as upload_file,
        patch(
            "app.services.files.FileService.delete_raw_extraction",
            new=AsyncMock(return_value=True),
        ) as delete_replaced_raw,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={
                "purpose": "cv",
                "replaces_raw_extraction_id": ("55555555-5555-4555-8555-555555555555"),
            },
            files={"file": ("cv.pdf", b"%PDF-1.7", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json()["text"] == "EDUCATION\n\nSoonchunhyang University"
    assert response.json()["layout_data"][0]["page"] == 1
    assert response.json()["layout_data"][0]["page_height"] == 842
    assert response.json()["layout_data"][0]["source_line_id"] == "p2-b1"
    assert response.json()["layout_data"][1]["source_line_id"] == "p2-b2"
    assert response.json()["raw_extraction_ref"] == {
        "id": persisted_raw_id,
        "extraction_version": "2.0",
        "method": "native_blocks",
    }
    persisted_payload = json.loads(upload_file.await_args_list[0].kwargs["data"])
    assert persisted_payload["pages"][0]["blocks"][0]["block_id"] == "p2-b1"
    assert upload_file.await_args_list[0].kwargs["bucket"] == RAW_EXTRACTION_BUCKET
    assert upload_file.await_args_list[0].kwargs["content_type"] == (
        "application/vnd.daucv.raw-extraction+json"
    )
    assert upload_file.await_args_list[0].kwargs["include_url"] is False
    assert upload_file.await_args_list[1].kwargs["bucket"] == "cv"
    assert upload_file.await_args_list[1].kwargs["content_type"] == "application/pdf"
    delete_replaced_raw.assert_awaited_once()
    assert "url" not in response.json()["raw_extraction_ref"]
    assert "pending_raw_extraction_cleanup_ids" not in response.json()
    extract_blocks.assert_called_once_with(b"%PDF-1.7")


def test_extract_pdf_does_not_return_flattened_success_when_raw_persistence_fails(
    client: TestClient,
) -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )

    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Synthetic content that must not appear in the error response",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    old_raw_id = "55555555-5555-4555-8555-555555555555"
    with (
        patch("app.api.routes.user.extract_cv_content_blocks", return_value=raw),
        patch(
            "app.services.files.FileService.upload_file",
            new=AsyncMock(side_effect=RuntimeError("storage unavailable")),
        ),
        patch(
            "app.services.files.FileService.delete_raw_extraction",
            new=AsyncMock(),
        ) as delete_replaced_raw,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={
                "purpose": "cv",
                "replaces_raw_extraction_id": old_raw_id,
            },
            files={"file": ("synthetic.pdf", b"%PDF-1.7", "application/pdf")},
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "PDF extraction failed. Please try again."}
    delete_replaced_raw.assert_not_awaited()


def test_extract_pdf_replacement_extraction_failure_preserves_old_raw(
    client: TestClient,
) -> None:
    old_raw_id = "55555555-5555-4555-8555-555555555555"
    with (
        patch(
            "app.api.routes.user.extract_cv_content_blocks",
            side_effect=RuntimeError("synthetic extraction failure"),
        ) as extract_blocks,
        patch(
            "app.services.files.FileService.delete_raw_extraction",
            new=AsyncMock(),
        ) as delete_replaced_raw,
        patch(
            "app.services.files.FileService.upload_file",
            new=AsyncMock(),
        ) as upload_file,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={
                "purpose": "cv",
                "replaces_raw_extraction_id": old_raw_id,
            },
            files={"file": ("cv.pdf", b"%PDF-1.7", "application/pdf")},
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "PDF extraction failed. Please try again."}
    extract_blocks.assert_called_once()
    delete_replaced_raw.assert_not_awaited()
    upload_file.assert_not_awaited()


def test_extract_pdf_returns_new_ref_and_pending_old_id_when_retirement_fails(
    client: TestClient,
) -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )

    old_raw_id = "55555555-5555-4555-8555-555555555555"
    new_raw_id = "66666666-6666-4666-8666-666666666666"
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Synthetic replacement content",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    with (
        patch("app.api.routes.user.extract_cv_content_blocks", return_value=raw),
        patch(
            "app.services.files.FileService.upload_file",
            new=AsyncMock(side_effect=[{"id": new_raw_id}, {"id": "source-pdf-id"}]),
        ) as upload_file,
        patch(
            "app.services.files.FileService.delete_raw_extraction",
            new=AsyncMock(side_effect=RuntimeError("private storage unavailable")),
        ) as delete_replaced_raw,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={
                "purpose": "cv",
                "replaces_raw_extraction_id": old_raw_id,
            },
            files={"file": ("cv.pdf", b"%PDF-1.7", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json()["raw_extraction_ref"]["id"] == new_raw_id
    assert response.json()["pending_raw_extraction_cleanup_ids"] == [old_raw_id]
    assert upload_file.await_count == 2
    delete_replaced_raw.assert_awaited_once_with(
        "12345678-1234-1234-1234-123456789012",
        old_raw_id,
    )


def test_extract_pdf_does_not_retire_when_old_and_new_raw_ids_match(
    client: TestClient,
) -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )

    shared_raw_id = "77777777-7777-4777-8777-777777777777"
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Synthetic same-id replacement content",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    with (
        patch("app.api.routes.user.extract_cv_content_blocks", return_value=raw),
        patch(
            "app.services.files.FileService.upload_file",
            new=AsyncMock(side_effect=[{"id": shared_raw_id}, {"id": "source-pdf-id"}]),
        ),
        patch(
            "app.services.files.FileService.delete_raw_extraction",
            new=AsyncMock(),
        ) as delete_replaced_raw,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={
                "purpose": "cv",
                "replaces_raw_extraction_id": shared_raw_id,
            },
            files={"file": ("cv.pdf", b"%PDF-1.7", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json()["raw_extraction_ref"]["id"] == shared_raw_id
    assert "pending_raw_extraction_cleanup_ids" not in response.json()
    delete_replaced_raw.assert_not_awaited()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_failed_raw_cleanup_survives_reload_then_retries_without_analysis_ref() -> None:
    module = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/lib/raw-extraction-lifecycle.ts"
    ).as_uri()
    script = f"""
import {{
  attemptNextRawExtractionCleanup,
  invalidateRawExtraction,
  normalizeRawExtractionLifecycle,
}} from {json.dumps(module)};

const reference = {{
  id: "11111111-1111-4111-8111-111111111111",
  extraction_version: "2.0",
  method: "native_blocks",
}};
let state = normalizeRawExtractionLifecycle({{
  rawExtractionRef: reference,
  pendingRawExtractionCleanupIds: [],
}});
state = invalidateRawExtraction(state);
const analysisReferenceAfterInvalidation = state.rawExtractionRef;

let failed = false;
try {{
  state = await attemptNextRawExtractionCleanup(state, async () => {{
    throw new Error("temporary network failure");
  }});
}} catch {{
  failed = true;
}}
const pendingAfterFailure = [...state.pendingRawExtractionCleanupIds];

// Simulate sessionStorage serialization and a subsequent reload.
state = normalizeRawExtractionLifecycle(JSON.parse(JSON.stringify(state)));
const pendingAfterReload = [...state.pendingRawExtractionCleanupIds];
const retriedIds = [];
state = await attemptNextRawExtractionCleanup(state, async (id) => {{
  retriedIds.push(id);
}});

process.stdout.write(JSON.stringify({{
  failed,
  analysisReferenceAfterInvalidation,
  pendingAfterFailure,
  pendingAfterReload,
  retriedIds,
  pendingAfterSuccess: state.pendingRawExtractionCleanupIds,
}}));
"""
    completed = subprocess.run(
        [
            "node",
            "--no-warnings",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    expected_id = "11111111-1111-4111-8111-111111111111"

    assert result["failed"] is True
    assert result["analysisReferenceAfterInvalidation"] is None
    assert result["pendingAfterFailure"] == [expected_id]
    assert result["pendingAfterReload"] == [expected_id]
    assert result["retriedIds"] == [expected_id]
    assert result["pendingAfterSuccess"] == []


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_pending_cleanup_wins_over_inconsistent_live_reference_on_reload() -> None:
    module = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/lib/raw-extraction-lifecycle.ts"
    ).as_uri()
    artifact_id = "22222222-2222-4222-8222-222222222222"
    script = f"""
import {{ normalizeRawExtractionLifecycle }} from {json.dumps(module)};
const state = normalizeRawExtractionLifecycle({{
  rawExtractionRef: {{
    id: {json.dumps(artifact_id)},
    extraction_version: "2.0",
    method: "word_layout",
  }},
  pendingRawExtractionCleanupIds: [{json.dumps(artifact_id)}],
}});
process.stdout.write(JSON.stringify(state));
"""
    completed = subprocess.run(
        [
            "node",
            "--no-warnings",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["rawExtractionRef"] is None
    assert result["pendingRawExtractionCleanupIds"] == [artifact_id]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_server_pending_cleanup_keeps_only_new_raw_reference_eligible() -> None:
    module = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/lib/raw-extraction-lifecycle.ts"
    ).as_uri()
    old_id = "33333333-3333-4333-8333-333333333333"
    new_id = "44444444-4444-4444-8444-444444444444"
    script = f"""
import {{
  acceptRawExtractionReference,
  queueRawExtractionCleanup,
}} from {json.dumps(module)};
let state = {{
  rawExtractionRef: {{
    id: {json.dumps(old_id)},
    extraction_version: "2.0",
    method: "native_blocks",
  }},
  pendingRawExtractionCleanupIds: [],
}};
state = acceptRawExtractionReference(state, {{
  id: {json.dumps(new_id)},
  extraction_version: "2.0",
  method: "word_layout",
}});
state = queueRawExtractionCleanup(state, [{json.dumps(old_id)}]);
const replacementState = state;
const sameIdTamperState = queueRawExtractionCleanup(state, [{json.dumps(new_id)}]);
process.stdout.write(JSON.stringify({{ replacementState, sameIdTamperState }}));
"""
    completed = subprocess.run(
        [
            "node",
            "--no-warnings",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["replacementState"]["rawExtractionRef"]["id"] == new_id
    assert result["replacementState"]["pendingRawExtractionCleanupIds"] == [old_id]
    assert result["sameIdTamperState"]["rawExtractionRef"] is None


def test_extract_pdf_jd_purpose_does_not_persist_raw_artifact(
    client: TestClient,
) -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )

    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Synthetic job description content for route coverage",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    with (
        patch("app.api.routes.user.extract_cv_content_blocks", return_value=raw),
        patch(
            "app.services.files.FileService.upload_file",
            new=AsyncMock(return_value={"id": "source-id"}),
        ) as upload_file,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={"purpose": "jd"},
            files={"file": ("synthetic.pdf", b"%PDF-1.7", "application/pdf")},
        )

    assert response.status_code == 200
    assert "raw_extraction_ref" not in response.json()
    upload_file.assert_awaited_once()
    assert upload_file.await_args.kwargs["bucket"] == "cv"
    assert upload_file.await_args.kwargs["content_type"] == "application/pdf"


def test_extract_pdf_rejects_oversize_before_extraction(client: TestClient) -> None:
    with (
        patch("app.api.routes.user.PDF_MAX_SIZE", 8),
        patch("app.api.routes.user.extract_cv_content_blocks") as extract_blocks,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={"purpose": "cv"},
            files={"file": ("synthetic.pdf", b"%PDF-1.7-oversize", "application/pdf")},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "PDF exceeds the maximum allowed size."}
    extract_blocks.assert_not_called()


def test_extract_pdf_post_read_size_check_handles_inaccurate_metadata() -> None:
    from fastapi import HTTPException, UploadFile
    from starlette.datastructures import Headers

    from app.api.routes.user import extract_pdf

    upload = UploadFile(
        file=io.BytesIO(b"%PDF-1.7-oversize"),
        size=0,
        filename="synthetic.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    with (
        patch("app.api.routes.user.PDF_MAX_SIZE", 8),
        patch("app.api.routes.user.extract_cv_content_blocks") as extract_blocks,
        pytest.raises(HTTPException) as exc_info,
    ):
        asyncio.run(
            extract_pdf(
                file=upload,
                purpose="cv",
                replaces_raw_extraction_id=None,
                user={"id": "owner"},
                file_service=AsyncMock(),
            )
        )

    assert exc_info.value.status_code == 413
    extract_blocks.assert_not_called()


def test_extract_pdf_production_route_falls_back_and_preserves_reading_order(
    client: TestClient,
) -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        ExtractionReason,
        RawBlock,
        RawExtraction,
        RawPage,
    )

    pdf_bytes = _make_positioned_pdf(
        [
            (48, 48, "SYNTHETIC CANDIDATE"),
            (360, 48, "candidate@example.test"),
            (48, 160, "CAREER OBJECTIVE"),
            (360, 160, "TECHNICAL SKILLS"),
            (48, 190, "Build reliable logistics systems for regional operations"),
            (360, 190, "Python SQL forecasting and warehouse analytics"),
            (48, 220, "EDUCATION"),
            (360, 220, "LANGUAGES"),
            (48, 250, "Synthetic University Bachelor of Economics 2024"),
            (360, 250, "English professional working proficiency"),
            (48, 280, "EXPERIENCE"),
            (360, 280, "ACTIVITIES"),
            (48, 310, "Operations intern improved dispatch documentation accuracy"),
            (360, 310, "Organized student events and partner outreach programs"),
        ]
    )
    scrambled_native = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        warnings=[ExtractionReason.POSSIBLE_COLUMN_INTERLEAVING.value],
        pages=[
            RawPage(
                page=1,
                width=612,
                height=792,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text=(
                            "CAREER OBJECTIVE TECHNICAL SKILLS EDUCATION LANGUAGES "
                            "EXPERIENCE ACTIVITIES synthetic extraction content "
                            "with enough characters to pass text-only checks"
                        ),
                        bbox=(48, 150, 550, 320),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    raw_id = "33333333-3333-4333-8333-333333333333"
    with (
        patch(
            "app.services.layout_extraction.extract_native_blocks",
            return_value=scrambled_native,
        ),
        patch(
            "app.services.files.FileService.upload_file",
            new=AsyncMock(side_effect=[{"id": raw_id}, {"id": "source-id"}]),
        ) as upload_file,
    ):
        response = client.post(
            "/api/extract-pdf",
            data={"purpose": "cv"},
            files={"file": ("synthetic.pdf", pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["raw_extraction_ref"]["id"] == raw_id
    persisted = json.loads(upload_file.await_args_list[0].kwargs["data"])
    assert persisted["method"] == "word_layout"
    blocks = persisted["pages"][0]["blocks"]
    assert [block["block_id"] for block in blocks] == [
        f"p1-b{index}" for index in range(1, len(blocks) + 1)
    ]
    assert [block["reading_order"] for block in blocks] == list(range(len(blocks)))
    texts = [block["text"] for block in blocks]
    assert texts.index("CAREER OBJECTIVE") < texts.index("EXPERIENCE")
    assert texts.index("EXPERIENCE") < texts.index("TECHNICAL SKILLS")
    assert all(text != "CAREER OBJECTIVE TECHNICAL SKILLS" for text in texts)
    assert [line["source_line_id"] for line in body["layout_data"]] == [
        block["block_id"] for block in blocks
    ]

    from app.services.layout_extraction import extract_word_layout_blocks

    repeated = extract_word_layout_blocks(pdf_bytes)
    repeated_blocks = repeated.pages[0].blocks
    assert [
        (block.block_id, block.reading_order, block.text, block.bbox)
        for block in repeated_blocks
    ] == [
        (
            block["block_id"],
            block["reading_order"],
            block["text"],
            tuple(block["bbox"]),
        )
        for block in blocks
    ]


def test_real_cv_fixture_fallback_materially_improves_structure() -> None:
    from app.models.cv_raw_extraction import ExtractionMethod, ExtractionReason
    from app.services.cv_reconstruction_service import reconstruct_from_lines
    from app.services.layout_extraction import (
        evaluate_extraction,
        extract_cv_content_blocks,
        extract_native_blocks,
        raw_extraction_to_layout_lines,
    )

    fixture = Path(__file__).parent / "cv_test" / "CV_DUYNGUYEN_2pu.pdf"
    if not fixture.exists():
        pytest.skip("Local acceptance fixture is not available.")

    pdf_bytes = fixture.read_bytes()
    native_decision = evaluate_extraction(extract_native_blocks(pdf_bytes))
    selected = extract_cv_content_blocks(pdf_bytes)
    reconstructed = reconstruct_from_lines(raw_extraction_to_layout_lines(selected))

    assert native_decision.usable is False
    assert ExtractionReason.POSSIBLE_COLUMN_INTERLEAVING in native_decision.reasons
    assert selected.method == ExtractionMethod.WORD_LAYOUT
    assert "possible_column_order_problem" not in reconstructed.reconstruction_warnings
    assert (
        "summary_contains_embedded_headings"
        not in reconstructed.reconstruction_warnings
    )


def test_extraction_quality_is_conservative_for_logical_wide_rows() -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        ExtractionReason,
        RawBlock,
        RawExtraction,
        RawPage,
    )
    from app.services.layout_extraction import evaluate_extraction

    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                width=612,
                height=792,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="EXPERIENCE",
                        bbox=(36, 120, 576, 138),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b2",
                        page=1,
                        text="Software Engineer",
                        bbox=(36, 160, 180, 176),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b3",
                        page=1,
                        text="2023 - Present",
                        bbox=(470, 160, 576, 176),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b4",
                        page=1,
                        text=(
                            "Built reliable services and improved operational "
                            "documentation for a fictional regional platform."
                        ),
                        bbox=(36, 190, 430, 218),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b5",
                        page=1,
                        text=(
                            "Collaborated with product and support teams to deliver "
                            "measurable workflow improvements."
                        ),
                        bbox=(36, 225, 430, 253),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                ],
            )
        ],
    )

    decision = evaluate_extraction(raw)
    assert decision.usable is True
    assert ExtractionReason.POSSIBLE_COLUMN_INTERLEAVING not in decision.reasons

    embedded_heading = raw.model_copy(deep=True)
    embedded_heading.pages[0].blocks[0].text = "Professional Summary"
    embedded_decision = evaluate_extraction(embedded_heading)
    assert embedded_decision.usable is False
    assert ExtractionReason.POSSIBLE_COLUMN_INTERLEAVING in embedded_decision.reasons


def test_three_column_sort_uses_repeated_lanes_not_sparse_date_fragments() -> None:
    from app.models.cv_raw_extraction import ExtractionMethod, RawBlock
    from app.services.layout_extraction import sort_raw_page_blocks

    def block(block_id: str, text: str, x: float, y: float) -> RawBlock:
        return RawBlock(
            block_id=block_id,
            page=1,
            text=text,
            bbox=(x, y, x + 120, y + 16),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        )

    blocks = [
        block("right-2", "right column substantive second content entry", 420, 220),
        block("left-1", "left column substantive first content entry", 36, 150),
        block("middle-2", "middle column substantive second content entry", 228, 220),
        block("right-1", "right column substantive first content entry", 420, 150),
        block("left-2", "left column substantive second content entry", 36, 220),
        block("middle-1", "middle column substantive first content entry", 228, 150),
    ]
    ordered = sort_raw_page_blocks(blocks, page_width=612, page_height=792)
    assert [item.block_id for item in ordered] == [
        "left-1",
        "left-2",
        "middle-1",
        "middle-2",
        "right-1",
        "right-2",
    ]

    dated_rows = [
        block("role-1", "Synthetic Engineer", 36, 150),
        block("date-1", "2021 - 2022", 450, 150),
        block("role-2", "Synthetic Analyst", 36, 190),
        block("date-2", "2022 - 2023", 450, 190),
        block("role-3", "Synthetic Lead", 36, 230),
        block("date-3", "2023 - Present", 450, 230),
    ]
    dated_order = sort_raw_page_blocks(
        dated_rows,
        page_width=612,
        page_height=792,
    )
    assert [item.block_id for item in dated_order] == [
        "role-1",
        "date-1",
        "role-2",
        "date-2",
        "role-3",
        "date-3",
    ]


def test_raw_extraction_reference_is_privately_retrievable_by_owner() -> None:
    from app.core.config import RAW_EXTRACTION_BUCKET
    from app.models.cv_raw_extraction import ExtractionMethod
    from app.services.files import FileService

    class PrivateStorage:
        def __init__(self) -> None:
            self.downloaded = False

        async def download(self, bucket: str, path: str) -> bytes:
            self.downloaded = True
            assert (bucket, path) == (
                RAW_EXTRACTION_BUCKET,
                "owner/raw-extraction.json",
            )
            return b'{"extraction_version":"2.0","method":"native_blocks","pages":[]}'

    repository = AsyncMock()
    repository.get_file_by_id.return_value = {
        "id": "raw-id",
        "user_id": "owner",
        "bucket": RAW_EXTRACTION_BUCKET,
        "object_path": "owner/raw-extraction.json",
        "content_type": "application/vnd.daucv.raw-extraction+json",
    }
    storage = PrivateStorage()
    service = FileService(storage=storage, repository=repository)

    raw = asyncio.run(service.load_raw_extraction("owner", "raw-id"))
    denied = asyncio.run(service.load_raw_extraction("different-user", "raw-id"))

    assert raw is not None
    assert raw.method == ExtractionMethod.NATIVE_BLOCKS
    assert denied is None
    assert storage.downloaded is True

    repository.get_file_by_id.return_value = {
        **repository.get_file_by_id.return_value,
        "bucket": "cv",
        "content_type": "application/pdf",
    }
    assert asyncio.run(service.load_raw_extraction("owner", "raw-id")) is None


def test_raw_extraction_loader_rejects_malformed_private_artifact() -> None:
    from app.core.config import RAW_EXTRACTION_BUCKET
    from app.models.cv_raw_extraction import InvalidRawExtractionArtifactError
    from app.services.files import FileService

    class MalformedStorage:
        async def download(self, bucket: str, path: str) -> bytes:
            return b'{"method":"not-a-valid-method","pages":[]}'

    repository = AsyncMock()
    repository.get_file_by_id.return_value = {
        "id": "raw-id",
        "user_id": "owner",
        "bucket": RAW_EXTRACTION_BUCKET,
        "object_path": "owner/raw-extraction.json",
        "content_type": "application/vnd.daucv.raw-extraction+json",
    }
    service = FileService(storage=MalformedStorage(), repository=repository)

    with pytest.raises(InvalidRawExtractionArtifactError):
        asyncio.run(service.load_raw_extraction("owner", "raw-id"))


def test_private_raw_bucket_refuses_public_url_generation() -> None:
    from app.core.config import RAW_EXTRACTION_BUCKET
    from app.storage.supabase import SupabaseStorage

    storage = SupabaseStorage(
        supabase_url="https://storage.example.test",
        supabase_key="test-key",
    )
    with pytest.raises(ValueError, match="Public URLs are disabled"):
        asyncio.run(
            storage.get_url(
                RAW_EXTRACTION_BUCKET,
                "owner/raw-extraction.json",
            )
        )


def test_delete_raw_extraction_route_enforces_artifact_cleanup(
    client: TestClient,
) -> None:
    with patch(
        "app.services.files.FileService.delete_raw_extraction",
        new=AsyncMock(return_value=True),
    ) as delete_raw:
        response = client.delete(
            "/api/raw-extractions/44444444-4444-4444-8444-444444444444"
        )

    assert response.status_code == 204
    delete_raw.assert_awaited_once()


def test_file_service_deletes_only_owned_raw_extraction_artifacts() -> None:
    from app.core.config import RAW_EXTRACTION_BUCKET
    from app.services.files import FileService

    storage = AsyncMock()
    repository = AsyncMock()
    repository.get_file_by_id.return_value = {
        "id": "raw-id",
        "user_id": "owner",
        "bucket": RAW_EXTRACTION_BUCKET,
        "object_path": "owner/raw-extraction.json",
        "content_type": "application/vnd.daucv.raw-extraction+json",
    }
    repository.delete_file.return_value = True
    service = FileService(storage=storage, repository=repository)

    assert asyncio.run(service.delete_raw_extraction("owner", "raw-id")) is True
    storage.delete.assert_awaited_once_with(
        bucket=RAW_EXTRACTION_BUCKET,
        path="owner/raw-extraction.json",
    )

    repository.get_file_by_id.return_value = {
        **repository.get_file_by_id.return_value,
        "bucket": "cv",
        "content_type": "application/pdf",
    }
    assert asyncio.run(service.delete_raw_extraction("owner", "source-id")) is False
    assert storage.delete.await_count == 1


def test_file_service_rolls_back_object_when_metadata_persistence_fails() -> None:
    from app.services.files import FileService

    storage = AsyncMock()
    repository = AsyncMock()
    repository.create_file.side_effect = RuntimeError("metadata unavailable")
    service = FileService(storage=storage, repository=repository)

    with pytest.raises(RuntimeError, match="metadata unavailable"):
        asyncio.run(
            service.upload_file(
                user_id="owner",
                filename="raw-extraction-synthetic.json",
                data=b"{}",
                content_type="application/vnd.daucv.raw-extraction+json",
                bucket="cv-raw-private",
                include_url=False,
            )
        )

    storage.upload.assert_awaited_once()
    storage.delete.assert_awaited_once_with(
        bucket="cv-raw-private",
        path="owner/raw-extraction-synthetic.json",
    )


def test_file_service_rejects_empty_metadata_and_rolls_back_object() -> None:
    from app.services.files import FileService

    storage = AsyncMock()
    repository = AsyncMock()
    repository.create_file.return_value = {}
    service = FileService(storage=storage, repository=repository)

    with pytest.raises(RuntimeError, match="File metadata could not be persisted"):
        asyncio.run(
            service.upload_file(
                user_id="owner",
                filename="raw-extraction-empty-record.json",
                data=b"{}",
                content_type="application/vnd.daucv.raw-extraction+json",
                bucket="cv-raw-private",
                include_url=False,
            )
        )

    storage.delete.assert_awaited_once_with(
        bucket="cv-raw-private",
        path="owner/raw-extraction-empty-record.json",
    )


def test_file_service_rollback_failure_logs_generic_metadata_error(caplog) -> None:
    from app.services.files import FileService

    storage = AsyncMock()
    storage.delete.side_effect = RuntimeError("owner/private-object-path")
    repository = AsyncMock()
    repository.create_file.return_value = {}
    service = FileService(storage=storage, repository=repository)

    with pytest.raises(RuntimeError, match="File metadata could not be persisted"):
        asyncio.run(
            service.upload_file(
                user_id="owner",
                filename="private-object-path",
                data=b"private bytes",
                content_type="application/vnd.daucv.raw-extraction+json",
                bucket="cv-raw-private",
                include_url=False,
            )
        )

    assert "Failed to roll back file after metadata persistence error" in caplog.text
    assert "private-object-path" not in caplog.text
    assert "private bytes" not in caplog.text


def test_extract_pdf_empty_raw_metadata_rolls_back_new_and_preserves_old() -> None:
    from fastapi import HTTPException, UploadFile
    from starlette.datastructures import Headers

    from app.api.routes.user import extract_pdf
    from app.core.config import RAW_EXTRACTION_BUCKET
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )
    from app.services.files import FileService

    old_raw_id = "88888888-8888-4888-8888-888888888888"
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Synthetic metadata failure content",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    upload = UploadFile(
        file=io.BytesIO(b"%PDF-1.7"),
        size=8,
        filename="synthetic.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    storage = AsyncMock()
    repository = AsyncMock()
    repository.create_file.return_value = {}
    service = FileService(storage=storage, repository=repository)

    with (
        patch("app.api.routes.user.extract_cv_content_blocks", return_value=raw),
        pytest.raises(HTTPException) as exc_info,
    ):
        asyncio.run(
            extract_pdf(
                file=upload,
                purpose="cv",
                replaces_raw_extraction_id=old_raw_id,
                user={"id": "owner"},
                file_service=service,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "PDF extraction failed. Please try again."
    storage.upload.assert_awaited_once()
    rollback_call = storage.delete.await_args
    assert rollback_call.kwargs["bucket"] == RAW_EXTRACTION_BUCKET
    assert rollback_call.kwargs["path"].startswith("owner/raw-extraction-")
    assert rollback_call.kwargs["path"].endswith(".json")
    repository.get_file_by_id.assert_not_awaited()


def test_tailored_cv_create_requires_analysis_entitlement(client: TestClient) -> None:
    resp = client.post(
        "/api/user/tailored-cvs",
        json={
            "tailored_cv": {"name": "Duy", "sections": []},
            "source_cv_text": "Duy\nduy@example.com",
            "jd_text": "Backend Engineer",
        },
    )
    assert resp.status_code == 422


def test_tailored_cv_create_reports_required_persistence_migration(
    client: TestClient,
) -> None:
    from app.services.tailored_cv_service import CVPersistenceMigrationRequiredError

    with patch(
        "app.services.tailored_cv_service.create_version",
        new=AsyncMock(side_effect=CVPersistenceMigrationRequiredError()),
    ):
        response = client.post(
            "/api/user/tailored-cvs",
            json={
                "tailored_cv": {"name": "Duy", "sections": []},
                "source_cv_text": "Duy\nduy@example.com",
                "jd_text": "Backend Engineer",
                "tailoring_entitlement": "x" * 65,
            },
        )

    assert response.status_code == 503
    assert "nâng cấp" in response.json()["detail"]


def test_tailored_cv_routes_validate_version_id(client: TestClient) -> None:
    patch_response = client.patch(
        "/api/user/tailored-cvs/not-a-uuid",
        json={"selected_design": "modern_professional"},
    )
    pdf_response = client.get("/api/user/tailored-cvs/not-a-uuid/pdf")

    assert patch_response.status_code == 400
    assert pdf_response.status_code == 400


def test_tailored_cv_list_returns_controlled_future_schema_error(
    client: TestClient,
) -> None:
    from app.services.tailored_cv_service import UnsupportedCVSchemaVersionError

    with patch(
        "app.services.tailored_cv_service.list_versions",
        new=AsyncMock(side_effect=UnsupportedCVSchemaVersionError(3)),
    ):
        response = client.get("/api/user/tailored-cvs")

    assert response.status_code == 409
    assert "schema 3" in response.json()["detail"]


def test_analyze_cv_rejects_no_cv_text(client: TestClient) -> None:
    resp = client.post("/api/analyze-cv", json={"cv_text": ""})
    assert resp.status_code == 422


def test_analyze_cv_422_with_whitespace_only(client: TestClient) -> None:
    resp = client.post("/api/analyze-cv", json={"cv_text": "   "})
    assert resp.status_code == 422


def _analysis_without_phase5_diagnostics():
    from app.models.cv_document_v2 import (
        CVDocumentV2,
        CVReconstructionDiagnostics,
    )
    from app.models.responses import CVAnalysisResponse

    document = CVDocumentV2()
    return CVAnalysisResponse.model_validate(
        {
            "match_headline": "Synthetic result",
            "match_summary": "Synthetic analysis result.",
            "technical_match": 50,
            "experience_relevance": 50,
            "keyword_coverage": 50,
            "impact_evidence": 50,
            "tone_quality": 50,
            "ats_readiness": 50,
            "missing_keywords": [],
            "suggested_edits": [],
            "cv_strengths": [],
            "prioritized_keywords": [],
            "evidence_analysis": [],
            "role_fit_score": 50,
            "match_score": 50,
            "score_breakdown": {
                "weights": {},
                "raw_score": 50,
                "critical_missing_count": 0,
                "high_missing_count": 0,
                "weighted_missing_requirement_score": 0,
                "unsupported_claim_count": 0,
                "critical_missing_penalty": 0,
                "high_missing_penalty": 0,
                "missing_requirement_penalty": 0,
                "unsupported_claim_penalty": 0,
                "total_penalty": 0,
                "final_score": 50,
            },
            "document_v2": document,
            "source_document_v2": document,
            "reconstruction_diagnostics": CVReconstructionDiagnostics(),
            "tailoring_diagnostics": None,
        }
    )


def test_analyze_cv_missing_phase5_diagnostics_fails_instead_of_downgrading(
    client: TestClient,
) -> None:
    with (
        patch(
            "app.api.routes.user.cv_analysis_service.analyze_cv",
            new=AsyncMock(return_value=_analysis_without_phase5_diagnostics()),
        ),
        patch(
            "app.api.routes.user._refund_reserved_credit",
            new=AsyncMock(),
        ) as refund,
    ):
        response = client.post(
            "/api/analyze-cv",
            json={"cv_text": "Synthetic CV", "jd_text": "Synthetic JD"},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Phân tích CV thất bại. Vui lòng thử lại sau."
    refund.assert_awaited_once()


def test_analyze_cv_stream_missing_phase5_diagnostics_emits_error_not_complete(
    client: TestClient,
) -> None:
    with (
        patch(
            "app.api.routes.user.cv_analysis_service.analyze_cv",
            new=AsyncMock(return_value=_analysis_without_phase5_diagnostics()),
        ),
        patch(
            "app.api.routes.user._refund_reserved_credit",
            new=AsyncMock(),
        ) as refund,
    ):
        response = client.post(
            "/api/analyze-cv/stream",
            json={"cv_text": "Synthetic CV", "jd_text": "Synthetic JD"},
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    assert response.status_code == 200
    assert not any(event["type"] == "complete" for event in events)
    assert events[-1]["type"] == "error"
    assert events[-1]["status"] == 500
    refund.assert_awaited_once()


def test_analyze_cv_route_uses_owned_raw_ref_for_semantic_source(
    client: TestClient,
) -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )
    from app.models.cv_structuring import LLMSemanticCVResponse
    from app.models.responses import CVAnalysisGenerationResponse

    raw_ref_id = "99999999-9999-4999-8999-999999999999"
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="SYNTHETIC CANDIDATE",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b2",
                        page=1,
                        text="EXPERIENCE",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                    RawBlock(
                        block_id="p1-b3",
                        page=1,
                        text="Built a source-grounded service.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=2,
                    ),
                ],
            )
        ],
    )
    semantic = LLMSemanticCVResponse.model_validate(
        {
            "identity": {
                "full_name": "SYNTHETIC CANDIDATE",
                "field_source_block_ids": {"full_name": ["p1-b1"]},
            },
            "sections": [
                {
                    "type": "experience",
                    "title": "EXPERIENCE",
                    "source_block_ids": ["p1-b2"],
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "Built a source-grounded service.",
                            "source_block_ids": ["p1-b3"],
                        }
                    ],
                }
            ],
            "unmapped_references": [],
            "confidence": 0.95,
        }
    )
    analysis = CVAnalysisGenerationResponse.model_validate(
        {
            "match_headline": "Good fit",
            "match_summary": "The profile has relevant source-grounded experience.",
            "technical_match": 80,
            "experience_relevance": 80,
            "keyword_coverage": 75,
            "impact_evidence": 70,
            "tone_quality": 80,
            "ats_readiness": 80,
            "missing_keywords": [],
            "suggested_edits": [],
            "cv_strengths": [],
            "prioritized_keywords": [],
            "evidence_analysis": [],
        }
    )

    with (
        patch(
            "app.services.files.FileService.load_raw_extraction",
            new=AsyncMock(return_value=raw),
        ) as load_raw,
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new=AsyncMock(return_value=semantic),
        ),
        patch(
            "app.services.cv_analysis_service.call_llm_with_fallback",
            new=AsyncMock(return_value=analysis),
        ),
    ):
        response = client.post(
            "/api/analyze-cv",
            json={
                "cv_text": (
                    "SYNTHETIC CANDIDATE\nEXPERIENCE\nBuilt a source-grounded service."
                ),
                "jd_text": "Backend Engineer",
                "raw_extraction_ref_id": raw_ref_id,
                "layout_data": [
                    {
                        "text": "TAMPERED CLIENT LAYOUT",
                        "page": 99,
                        "x": 0,
                        "y": 0,
                        "width": 1,
                        "height": 1,
                    }
                ],
            },
        )

    assert response.status_code == 200, response.text
    source_document = response.json()["source_document_v2"]
    assert source_document["raw_extraction_id"] == raw_ref_id
    assert source_document["parser_version"] == "llm-semantic-1.0"
    assert source_document["identity"]["full_name"] == "SYNTHETIC CANDIDATE"
    assert "TAMPERED CLIENT LAYOUT" not in json.dumps(source_document)
    load_raw.assert_awaited_once_with(
        "12345678-1234-1234-1234-123456789012",
        raw_ref_id,
    )


def test_analyze_cv_owner_denied_raw_ref_refunds_credit(
    client: TestClient,
) -> None:
    raw_ref_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    with (
        patch(
            "app.services.files.FileService.load_raw_extraction",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new=AsyncMock(),
        ) as parser,
        patch(
            "app.api.routes.user._refund_reserved_credit",
            new=AsyncMock(),
        ) as refund,
    ):
        response = client.post(
            "/api/analyze-cv",
            json={
                "cv_text": "Synthetic candidate CV",
                "raw_extraction_ref_id": raw_ref_id,
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Raw extraction reference was not found."
    parser.assert_not_awaited()
    refund.assert_awaited_once()


def test_analyze_cv_times_out_and_refunds_reserved_credit(
    client: TestClient,
) -> None:
    async def slow_analysis(**_: object) -> None:
        await asyncio.sleep(1)

    with (
        patch(
            "app.api.routes.user.CV_ANALYSIS_REQUEST_TIMEOUT",
            0.01,
        ),
        patch(
            "app.api.routes.user.cv_analysis_service.analyze_cv",
            side_effect=slow_analysis,
        ),
        patch(
            "app.api.routes.user._refund_reserved_credit",
            new_callable=AsyncMock,
        ) as refund,
    ):
        response = client.post(
            "/api/analyze-cv",
            json={"cv_text": "Backend engineer", "jd_text": "Backend role"},
        )

    assert response.status_code == 504
    assert response.json()["detail"] == "CV analysis timed out. Please try again."
    refund.assert_awaited_once()


def test_writer_rejects_empty_cv(client: TestClient) -> None:
    resp = client.post(
        "/api/writer/generate",
        json={
            "cv_text": "",
            "writing_type": "email",
            "tone": "Chuyên nghiệp",
            "language": "vi",
        },
    )
    assert resp.status_code == 422


def test_writer_accepts_language_options(client: TestClient, monkeypatch: Any) -> None:
    from app.models.responses import WriterResponse

    async def mock_call_llm(*args: Any, **kwargs: Any) -> WriterResponse:
        return WriterResponse(
            subject_line="Subject",
            content="Content",
            tips=["Tip 1"],
        )

    monkeypatch.setattr("app.api.routes.user.call_llm_with_fallback", mock_call_llm)

    for lang in ["vi", "en", "auto"]:
        resp = client.post(
            "/api/writer/generate",
            json={
                "cv_text": "Software Engineer CV",
                "writing_type": "email",
                "tone": "Chuyên nghiệp",
                "language": lang,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Content"


def test_interview_chat_accepts_empty_history_first_turn(client: TestClient) -> None:
    """Empty chat history on first turn is valid — the route has special first-turn logic."""
    resp = client.post(
        "/api/interview/chat",
        json={
            "cv_text": "Test CV",
            "chat_history": [],
            "current_question": 1,
            "total_questions": 5,
        },
    )
    # Should NOT be 422 — the route handles first turn specially
    assert resp.status_code != 422


def test_interview_finish_rejects_empty_history(client: TestClient) -> None:
    resp = client.post(
        "/api/interview/finish",
        json={
            "cv_text": "Test CV",
            "chat_history": [],
            "interview_type": "general",
        },
    )
    assert resp.status_code == 422


def test_parse_profile_rejects_empty_cv(client: TestClient) -> None:
    resp = client.post("/api/jobs/parse-profile", json={"cv_text": ""})
    assert resp.status_code == 422


def test_tts_rejects_empty_text(client: TestClient) -> None:
    resp = client.post("/api/interview/tts", json={"text": ""})
    assert resp.status_code == 400


def test_tts_rejects_no_body(client: TestClient) -> None:
    resp = client.post("/api/interview/tts", json={})
    assert resp.status_code == 422


def test_jobs_search_accepts_minimal_body(client: TestClient) -> None:
    """Job search failures must degrade to a response instead of an unhandled 500."""
    resp = client.post("/api/jobs/search", json={"cv_text": "Test CV"})
    assert resp.status_code == 200, resp.text


def test_get_user_profile(client: TestClient) -> None:
    resp = client.get("/api/user/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["credits"] == 10
    assert data["active_cv"]["cv_filename"] == "test.pdf"
    assert "total_cvs" in data
    assert "active_cv_age_days" in data


def test_list_user_cvs(client: TestClient) -> None:
    resp = client.get("/api/user/cvs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["cvs"], list)
    assert len(data["cvs"]) == 1
    assert data["cvs"][0]["cv_filename"] == "test.pdf"


def test_upload_user_cv(client: TestClient) -> None:
    resp = client.post(
        "/api/user/cv",
        json={"cv_text": "Updated CV Text", "cv_filename": "updated_resume.pdf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cv_filename"] == "test.pdf"  # Returned by mock fetchrow
    assert data["cv_text"] == "Sample CV Text"


def test_update_active_cv(client: TestClient) -> None:
    resp = client.put(
        "/api/user/cv/active",
        json={"cv_text": "Draft CV Text", "cv_filename": "draft_resume.pdf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cv_filename"] == "test.pdf"  # Returned by mock fetchrow
    assert data["cv_text"] == "Sample CV Text"


def test_deactivate_user_cv(client: TestClient) -> None:
    cv_id = "12345678-1234-1234-1234-123456789012"
    resp = client.delete(f"/api/user/cv/{cv_id}")
    assert resp.status_code == 200
    assert resp.json() == {"success": True}


@patch(
    "app.api.routes.user.user_cv_service.submit_user_feedback",
    new_callable=AsyncMock,
)
def test_submit_feedback_route(mock_submit: AsyncMock, client: TestClient) -> None:
    mock_submit.return_value = (5, 15)  # 5 credits rewarded, new balance 15
    resp = client.post(
        "/api/user/feedback",
        json={"rating": 5, "content": "This application is amazing!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["credits_rewarded"] == 5
    assert data["new_credits"] == 15
    assert "Đóng góp thành công" in data["message"]


def test_list_feedbacks_route(client: TestClient) -> None:
    resp = client.get("/api/feedbacks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@patch(
    "app.api.routes.tailored_cv.tailored_cv_service.get_version",
    new_callable=AsyncMock,
)
def test_get_tailored_cv_pdf_ownership(mock_get: AsyncMock, client: TestClient) -> None:
    from app.services.tailored_cv_service import TailoredCVNotFoundError

    mock_get.side_effect = TailoredCVNotFoundError()

    resp = client.get("/api/user/tailored-cvs/12345678-1234-1234-1234-123456789012/pdf")
    assert resp.status_code == 404


@patch("app.services.cv_export_service.generate_pdf", new_callable=AsyncMock)
@patch(
    "app.services.cv_export_service.get_version",
    new_callable=AsyncMock,
)
def test_get_tailored_cv_pdf_downloads_pdf(
    mock_get: AsyncMock,
    mock_generate: AsyncMock,
    client: TestClient,
) -> None:
    from types import SimpleNamespace
    from uuid import UUID

    from app.models.cv_document_v2 import CVDocumentV2, CVIdentity
    from app.models.domain import TailoredCV

    version_id = UUID("12345678-1234-1234-1234-123456789012")
    mock_get.return_value = SimpleNamespace(
        id=version_id,
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        selected_design="classic_ats",
        template_id="classic_ats",
        template_version=1,
        document_v2=CVDocumentV2(identity=CVIdentity(full_name="Duy")),
        document_schema_version=2,
        reconstruction_version=1,
        reconstruction_status="current",
        source_language="vi",
    )
    mock_generate.return_value = b"%PDF-test"
    with patch(
        "app.services.cv_export_service.verify_exportable_v3_gates"
    ) as mock_verify:
        resp = client.get(f"/api/user/tailored-cvs/{version_id}/pdf")

        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF")
        assert resp.headers["content-type"] == "application/pdf"
        assert "attachment" in resp.headers["content-disposition"]


@patch(
    "app.api.routes.tailored_cv.tailored_cv_service.update_design",
    new_callable=AsyncMock,
)
def test_update_tailored_cv_design_ownership(
    mock_update: AsyncMock,
    client: TestClient,
) -> None:
    from app.services.tailored_cv_service import TailoredCVNotFoundError

    mock_update.side_effect = TailoredCVNotFoundError()

    resp = client.patch(
        "/api/user/tailored-cvs/12345678-1234-1234-1234-123456789012",
        json={"selected_design": "modern_professional"},
    )
    assert resp.status_code == 404


@patch(
    "app.api.routes.tailored_cv.tailored_cv_service.delete_version",
    new_callable=AsyncMock,
)
def test_delete_tailored_cv_version_ownership(
    mock_delete: AsyncMock,
    client: TestClient,
) -> None:
    from app.services.tailored_cv_service import TailoredCVNotFoundError

    mock_delete.side_effect = TailoredCVNotFoundError()

    resp = client.delete("/api/user/tailored-cvs/12345678-1234-1234-1234-123456789012")
    assert resp.status_code == 404


def test_verify_edit_rejects_unrelated_prior_token_without_minting(
    client: TestClient,
) -> None:
    from app.models.cv_document_v2 import CVDocumentV2, CVTailoringDiagnostics
    from app.services.tailored_cv_metadata import canonical_source_document_hash

    source = CVDocumentV2()
    diagnostics = CVTailoringDiagnostics(
        source_document_hash=canonical_source_document_hash(source),
        jd_hash="",
    )
    with patch(
        "app.services.cv_rewrite_service.issue_tailoring_entitlement_v3",
    ) as issue_mock:
        response = client.post(
            "/api/user/tailored-cv/verify-edit",
            json={
                "source_cv_text": "Synthetic CV",
                "jd_text": "",
                "source_document_v2": source.model_dump(mode="json"),
                "current_tailored_document_v2": source.model_dump(mode="json"),
                "edited_document_v2": source.model_dump(mode="json"),
                "tailoring_diagnostics": diagnostics.model_dump(mode="json"),
                "tailoring_entitlement": "x" * 65,
            },
        )

    assert response.status_code == 400
    issue_mock.assert_not_called()
