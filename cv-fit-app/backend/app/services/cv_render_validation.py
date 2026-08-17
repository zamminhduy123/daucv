"""Phase 6 Three-Tiered Render Validation Gate."""

import logging
from html.parser import HTMLParser
from typing import Any

from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_template import CVRenderDiagnostics
from app.services.cv_render_ledger import CVRenderLedger

_logger = logging.getLogger(__name__)


class RenderValidationError(ValueError):
    """Raised when rendering output fails any tier of the render quality gate."""

    def __init__(self, diagnostics: CVRenderDiagnostics, details: str) -> None:
        super().__init__(f"CV Render Validation Failed: {details}")
        self.diagnostics = diagnostics


class CVHTMLParser(HTMLParser):
    """HTML Parser for extracting elements with data-field-id to verify content conservation."""

    def __init__(self) -> None:
        super().__init__()
        self.field_contents: dict[str, list[str]] = {}
        self.current_field_id: str | None = None
        self.depth = 0
        self.all_field_ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        fid = attrs_dict.get("data-field-id")
        if fid:
            self.current_field_id = fid
            self.depth = 1
            self.field_contents.setdefault(fid, [])
            self.all_field_ids.append(fid)
        elif self.current_field_id:
            self.depth += 1

    def handle_data(self, data: str) -> None:
        if self.current_field_id:
            self.field_contents[self.current_field_id].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current_field_id:
            self.depth -= 1
            if self.depth == 0:
                self.current_field_id = None


def validate_static_html(
    html: str,
    ledger: CVRenderLedger,
    diagnostics: CVRenderDiagnostics,
) -> None:
    """Validate static HTML string against render ledger for Tier 1 conservation."""
    parser = CVHTMLParser()
    parser.feed(html)

    missing: list[str] = []
    duplicate: list[str] = []
    mismatched: list[str] = []

    # 1. Verify ledger items
    for field_id, item in ledger.items.items():
        occurrences = parser.all_field_ids.count(field_id)
        if occurrences == 0:
            missing.append(field_id)
            continue
        elif occurrences > item.expected_count:
            duplicate.append(field_id)

        # Decode actual text from elements and compare to expected text
        actual_text = "".join(parser.field_contents.get(field_id, [])).strip()
        expected_text = item.expected_text.strip()
        if actual_text != expected_text:
            mismatched.append(field_id)

        # Check escaping: literal unescaped expected text must not reside directly in raw HTML if it contains special tags/entities
        if any(c in expected_text for c in "<>&") and expected_text in html:
            mismatched.append(f"{field_id}:unescaped")

    # 2. Reject unknown field IDs in the parsed template HTML
    for fid in parser.all_field_ids:
        if fid not in ledger.items:
            mismatched.append(f"unknown:{fid}")

    diagnostics.missing_field_ids = missing
    diagnostics.duplicate_field_ids = duplicate
    diagnostics.mismatched_field_ids = mismatched
    diagnostics.is_valid = (
        len(missing) == 0 and len(duplicate) == 0 and len(mismatched) == 0
    )


async def validate_render_output(
    document: CVDocumentV2,
    html: str,
    ledger: CVRenderLedger,
    diagnostics: CVRenderDiagnostics,
    *,
    run_playwright: bool = False,
) -> None:
    """Execute Tier 1 (Static Conservation) and optional Tier 2 (Playwright Layout) validation gates.

    Raises RenderValidationError if any critical check fails.
    """
    # Tier 1: Static Conservation Gate
    validate_static_html(html, ledger, diagnostics)

    if not diagnostics.is_valid:
        details: list[str] = []
        if diagnostics.missing_field_ids:
            details.append(f"Missing field IDs: {diagnostics.missing_field_ids}")
        if diagnostics.duplicate_field_ids:
            details.append(f"Duplicate field IDs: {diagnostics.duplicate_field_ids}")
        if diagnostics.mismatched_field_ids:
            details.append(
                f"Mismatched/unescaped field IDs: {diagnostics.mismatched_field_ids}"
            )
        raise RenderValidationError(diagnostics, "; ".join(details))

    # Tier 2: Browser Layout Gate (Playwright bounding box layout inspection & PDF print)
    pdf_bytes: bytes | None = None
    if run_playwright:
        pdf_bytes = await _run_playwright_layout_gate(html, diagnostics)

    diagnostics.is_valid = True
    return pdf_bytes


async def _run_playwright_layout_gate(
    html: str, diagnostics: CVRenderDiagnostics
) -> bytes | None:
    """Inspect DOM layout and print PDF using Playwright in a single browser session."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        _logger.info("Playwright not installed; skipping browser layout gate.")
        return None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 794, "height": 1123})

        # Network isolation: block external URLs
        await page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.url.startswith("http")
            else route.continue_(),
        )

        await page.set_content(html, wait_until="domcontentloaded")
        await page.evaluate("document.fonts.ready")

        # 1. DOM Bounding Box & Visibility Inspection
        boxes: list[dict[str, Any]] = await page.evaluate("""() => {
            const elements = Array.from(document.querySelectorAll('[data-field-id]'));
            const leaves = elements.filter(el => el.querySelectorAll('[data-field-id]').length === 0);
            return leaves.map(el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const clientRects = Array.from(el.getClientRects()).map(r => ({
                    left: r.left,
                    top: r.top,
                    right: r.right,
                    bottom: r.bottom,
                    width: r.width,
                    height: r.height,
                }));
                return {
                    field_id: el.getAttribute('data-field-id'),
                    text: el.textContent.trim(),
                    left: rect.left,
                    top: rect.top,
                    right: rect.right,
                    bottom: rect.bottom,
                    width: rect.width,
                    height: rect.height,
                    scrollWidth: el.scrollWidth,
                    scrollHeight: el.scrollHeight,
                    display: style.display,
                    visibility: style.visibility,
                    clientRects: clientRects.length > 0 ? clientRects : [{
                        left: rect.left,
                        top: rect.top,
                        right: rect.right,
                        bottom: rect.bottom,
                        width: rect.width,
                        height: rect.height,
                    }],
                };
            });
        }""")

        clipped: list[str] = []
        overlapping: list[str] = []
        page_width = 794.0

        for box in boxes:
            fid = box["field_id"]
            # Check horizontal overflow or hidden/zero-sized elements
            if (
                box["right"] > page_width + 1.0
                or box["scrollWidth"] > box["width"] + 2.0
            ):
                clipped.append(fid)
            elif box["display"] == "none" or box["visibility"] == "hidden":
                clipped.append(f"{fid}:hidden")
            elif box["text"] and (box["width"] == 0 or box["height"] == 0):
                clipped.append(f"{fid}:zero_size")

        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                b1 = boxes[i]
                b2 = boxes[j]

                for r1 in b1["clientRects"]:
                    for r2 in b2["clientRects"]:
                        horiz_overlap = not (
                            r1["right"] <= r2["left"] or r1["left"] >= r2["right"]
                        )
                        vert_overlap = not (
                            r1["bottom"] <= r2["top"] or r1["top"] >= r2["bottom"]
                        )

                        if horiz_overlap and vert_overlap:
                            dx = min(r1["right"], r2["right"]) - max(
                                r1["left"], r2["left"]
                            )
                            dy = min(r1["bottom"], r2["bottom"]) - max(
                                r1["top"], r2["top"]
                            )
                            overlap_area = dx * dy

                            if overlap_area > 50.0:
                                pair = f"{b1['field_id']}<->{b2['field_id']}"
                                if pair not in overlapping:
                                    overlapping.append(pair)

        diagnostics.clipped_field_ids = clipped
        diagnostics.overlapping_field_ids = overlapping

        if clipped or overlapping:
            await browser.close()
            details_list: list[str] = []
            if clipped:
                details_list.append(f"Clipped/hidden fields: {clipped}")
            if overlapping:
                details_list.append(f"Overlapping leaf fields: {overlapping}")
            diagnostics.is_valid = False
            raise RenderValidationError(diagnostics, "; ".join(details_list))

        # 2. PDF Print Generation & Page Count Inspection
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
        )
        await browser.close()

        # Page count inspection
        try:
            import io

            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
            diagnostics.page_count = page_count
            if page_count > 3:
                diagnostics.is_valid = False
                raise RenderValidationError(
                    diagnostics, f"Page count excessive: {page_count} > 3 pages"
                )
        except Exception as exc:
            if isinstance(exc, RenderValidationError):
                raise
            _logger.warning("Could not parse PDF page count: %s", exc)

        return pdf_bytes
