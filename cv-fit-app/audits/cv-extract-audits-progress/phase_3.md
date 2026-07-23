# Phase 3 — Build layout-aware extraction

**Status:** Reviewed and corrected (uncommitted)  
**Implementation date:** 2026-07-15  
**Review date:** 2026-07-15  
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 3 (Steps 3.1–3.4)

## Review outcome

The initial Phase 3 implementation was not ready: its targeted suite reported
21 failures, 71 passes, and 2 skipped integration tests. The review found
several output-corrupting defects. They were fixed directly in the Phase 3
implementation and regression-tested.

| Severity | Finding | Resolution |
|---|---|---|
| P0 | `pdfplumber.extra_attrs` included glyph `width` and `height`, which participate in word grouping and could split normal words into fragments. | Only stable `fontname` and `size` attributes are requested. Line width and height now come from the complete line bounding box. |
| P0 | Multi-column sorting emitted every page once per `(page, column)` group, duplicating all content. | Sorting now iterates each page once and has a regression assertion for output cardinality. |
| P0 | Distinct x start positions were treated as columns, so indentation or a centered heading could reorder a single-column CV. | Columns are detected per page from line bounding boxes and horizontal gutters. Broad/spanning lines are handled as reading-order bands. |
| P0 | Non-bullet lines could never be joined because continuation detection ended with an unconditional `False`. | Continuation now combines geometry, typography, punctuation, section/boundary checks, and simple grammatical signals. |
| P0 | Cross-page joining compared page-local y coordinates directly and could not accept a normal bottom-to-top transition. | Cross-page joins now require matching columns/indentation/style plus previous-page bottom and next-page top proximity using `page_height`. |
| P0 | Joined fragments were still separated by `\n` in reconstructed plain text. | Reconstruction appends joined fragments to the current logical line and repairs trailing-hyphen word breaks. |
| P1 | Bullet variants, dash bullets, repeated spaces, and `PAGE N` markers did not normalize as documented. | Bullet/page regexes and whitespace normalization were corrected; NFKC normalization was added. |
| P1 | Repeated headers/footers and standalone page numbers were not handled. | Repeated normalized margin text and margin page numbers are flagged and suppressed from the returned content lines. |
| P1 | Words were grouped by exact floating-point top coordinates. | Visual lines now cluster word tops with a 2-point tolerance. |
| P1 | Multi-page extraction reused the final page width for every page. | Column assignment now uses each page's own width. |
| P2 | Tests encoded the wrong y-axis direction, expected soft-hyphen removal to invent an accent, and skipped all real-PDF checks when ReportLab was absent. | Fixtures now use pdfplumber's top-origin coordinates, the soft-hyphen expectation is correct, and a dependency-free real PDF regression test exercises pdfplumber directly. |

## Files reviewed and edited

| File | Result |
|---|---|
| `backend/app/services/layout_extraction.py` | Corrected metadata extraction, normalization, artifact removal, page-local column detection, reading order, continuations, and text reconstruction. |
| `backend/app/utils/helpers.py` | Keeps the legacy `extract_text_from_pdf()` import path while delegating to the layout-aware service. |
| `backend/tests/test_layout_extraction.py` | Corrected invalid tests and added regressions for every blocking review finding. |
| `audits/cv-extract-audits-progress/phase_3.md` | Replaced unverified completion claims with this reviewed implementation record. |

## Implemented behavior

### Step 3.1 — Preserve extraction metadata

`ExtractedLine` retains the original `text` and exposes:

- `page`, `x`, `y`, `width`, and `height`
- inferred `font_size` and `font_weight`
- `bullet_marker`
- `normalized_text`, `column_id`, and `joined_to_prev`
- page/artifact metadata used by normalization and cross-page checks

The extractor requests stable word attributes from pdfplumber, groups nearby
word tops into physical lines, and calculates each line's complete bounding box.

### Step 3.2 — Normalize extraction noise

The pipeline now handles:

- Unicode and dash/hyphen bullet variants, normalized to `•`
- repeated whitespace, tabs, soft hyphens, zero-width spaces, and NBSPs
- Unicode compatibility normalization with NFKC
- joined-line word breaks such as `inter-` + `national`
- explicit `PAGE N` / `TRANG N` markers
- repeated identical headers/footers in the 72-point page margins
- standalone page numbers in the page margins
- empty extraction results

Original and normalized text remain separate on each returned content line.
Layout artifacts are detected before column analysis and omitted from the
content-line result.

### Step 3.3 — Detect reading order

Column lanes are detected independently for each page from horizontal line
bounds. Wide lines do not erase a genuine gutter, and spanning headings divide
the page into reading-order bands. Lines are emitted page by page; within each
band, columns are read left-to-right and lines top-to-bottom. This avoids both
sidebar/main interleaving and the former duplicate-page bug.

Page transitions remain explicit through the zero-based `page` field, with
`page_height` retained for cross-page continuation checks.

### Step 3.4 — Detect physical line continuation

Continuation requires agreement among multiple signals:

- same or consecutive page
- same detected column
- plausible vertical gap or bottom-to-top page transition
- similar indentation
- similar font size and weight when available
- no page marker, section heading, date, role, or company boundary
- no terminal punctuation on the previous line
- bullet continuation rules or a plausible open/lowercase continuation

Capitalization alone never decides continuation. Reconstructed legacy text now
contains one newline per logical line and spaces (or repaired word breaks) for
physical continuations.

## Validation

Run from `backend/`:

| Check | Result |
|---|---|
| `./venv/bin/python -m pytest tests/test_layout_extraction.py -q` | **102 passed** |
| Real minimal-PDF extraction through pdfplumber | **Passed; words and line bounding boxes preserved** |
| `./venv/bin/ruff check app/services/layout_extraction.py app/utils/helpers.py tests/test_layout_extraction.py` | **Passed** |
| `./venv/bin/python -m py_compile ...` for the three Phase 3 Python files | **Passed** |
| Full backend suite excluding the browser-only PDF runtime file | **382 passed, 1 skipped** |
| Full backend suite | **381 passed, 1 skipped; 3 unrelated Playwright PDF-runtime tests could not launch Chromium in the filesystem sandbox (`MachPortRendezvousServer ... Permission denied`)** |

## Acceptance criteria

- [x] Step 3.1 metadata is preserved with original and normalized content.
- [x] Step 3.2 normalizes documented extraction noise and suppresses repeated margin artifacts/page numbers.
- [x] Step 3.3 detects page-local columns, preserves spanning boundaries, prevents duplicate output, and records page transitions.
- [x] Step 3.4 uses multiple continuation signals, including guarded cross-page continuation.
- [x] Existing `app.utils.helpers.extract_text_from_pdf()` callers remain compatible.
- [x] Targeted tests, lint, compilation, and a real pdfplumber extraction pass.

## Remaining limitations

1. Header/footer suppression requires identical normalized text on at least two pages; variable headers need a fuzzier matcher in a later phase.
2. Column and continuation thresholds remain heuristics and should be calibrated against the Phase 0 fixture corpus as more real layouts are added.
3. Font weight is inferred from font names and may be unavailable or inaccurate for custom embedded fonts.
4. Scanned/image-only PDFs still require OCR.
5. Grammatical plausibility is deliberately lightweight; semantic section and block reconstruction belong to Phases 4 and 5.

No commit was created as part of this review.
