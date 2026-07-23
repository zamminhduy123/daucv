# Phase 4 — Detect sections

**Status:** Implemented (uncommitted)
**Implementation date:** 2026-07-15
**Review date:** 2026-07-15
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 4 (Steps 4.1–4.3)

## Review outcome

Phase 4 replaces the three scattered section-heading vocabularies across
`layout_extraction.py`, `cv_quality_checks.py`, and `cv_v1_adapter.py` with a
single canonical vocabulary module, then wires a deterministic section detector
into the extraction pipeline so every `ExtractedLine` belongs to exactly one
section or the identity preamble.

| Severity | Finding | Resolution |
|---|---|---|
| P0 | Three separate heading vocabularies existed with overlapping but inconsistent sets. | Consolidated into `section_vocabulary.py` with NFKD decomposition + accent stripping. All lookups go through `classify_heading()`. |
| P0 | No section boundary detection existed outside the V1 adapter (which operated on LLM-produced `TailoredCV`, not raw lines). | New `section_detector.py` takes `list[ExtractedLine]` and produces `CVDocumentV2` using vocabulary + structural signals. |
| P1 | Structural signals (font size, separators, whitespace, position) were not combined for section detection. | `_detect_section_boundaries()` uses vocabulary first, then structural cues: font size ≥ 1.5 pt above baseline, short all-caps/title-case phrases, left margin alignment, separator proximity. |
| P1 | Identity preamble (name, headline, contact) was never extracted from raw lines. | `_detect_identity()` analyzes the first ≤ 5 content lines using name-length rules, headline-separator/keyword rules, and contact-pattern rules (email, phone, city). |
| P1 | Unknown headings could be silently dropped. | Unknown headings are classified as `"custom"` sections. Any unassigned content lines become an `"Other Content"` `CVUnknownBlock` with confidence 0.1. |
| P2 | No tests existed for section detection. | Full test suite (`test_section_detector.py`) covers vocabulary mapping, structural heading detection, identity/summary detection, boundary detection, custom section preservation, and end-to-end document construction. |

## Files reviewed and edited

| File | Result |
|---|---|
| `backend/app/services/section_vocabulary.py` | New — canonical vocabulary with `classify_heading()`, accent-stripped lookup, bilingual EN/VN support. |
| `backend/app/services/section_detector.py` | New — section boundary detection, identity extraction, summary detection, block classification, and `detect_sections()` entry point. |
| `backend/tests/test_section_detector.py` | New — 50+ parametrized tests covering all four step requirements plus edge cases. |
| `audits/cv-extract-audits-progress/phase_4.md` | This file. |

## Implemented behavior

### Step 4.1 — Canonical section vocabulary

`classify_heading(text)` returns `(canonical_type, display_text)` or `None`.
The vocabulary includes English and Vietnamese variants for all 11 canonical
section types plus a `"custom"` catch-all:

| Canonical type | Vietnamese variants |
|---|---|
| `summary` | tóm tắt, giới thiệu, mục tiêu, sơ lược |
| `experience` | kinh nghiệm, kinh nghiệm làm việc, quá trình làm việc |
| `projects` | dự án, dự án cá nhân, các dự án |
| `skills` | kỹ năng, kỹ năng chuyên môn, kỹ năng mềm, công nghệ |
| `education` | học vấn, học vấn và chứng chỉ |
| `publications` | công bố khoa học, công bố, bài báo khoa học |
| `certifications` | chứng chỉ, chứng chỉ nghề |
| `languages` | ngôn ngữ, ngôn ngữ giao tiếp |
| `awards` | giải thưởng |
| `activities` | hoạt động, hoạt động ngoại khóa, hoạt động tình nguyện |
| `interests` | sở thích |

The lookup is case-insensitive and diacritic-insensitive (NFKD decomposition
strips accents before matching).

### Step 4.2 — Combine deterministic and structural signals

Section boundaries are detected using two tiers:

1. **Deterministic** — `classify_heading()` matches against the canonical
   vocabulary. This is the primary signal.

2. **Structural** — when vocabulary doesn't match, a line is classified as a
   heading if it satisfies multiple structural signals:
   - Short phrase (≤ 5 words)
   - All-caps or title-case
   - Font size ≥ 1.5 pt above the document baseline
   - Left margin position (x ≤ 100)
   - Separator or blank line adjacent

No single signal is sufficient. A keyword alone does **not** make a heading.

### Step 4.3 — Preserve unknown sections

- Unrecognized headings → `"custom"` section with the original text as title.
- Lines not assigned to any section → `"Other Content"` `CVUnknownBlock` with
  `confidence: 0.1`.
- Nothing is silently dropped.

## Validation

Run from `backend/`:

| Check | Result |
|---|---|
| `./venv/bin/python -m app.services.section_vocabulary` | **Self-test passed (14/14 variants correct)** |
| Imports (`section_vocabulary`, `section_detector`) | **All imports verified OK** |
| `./venv/bin/python tests/_run_phase4_tests.py` | **Passed (34/34 assertions passed)** |
| `./venv/bin/pytest tests/test_section_detector.py` | **Passed (61/61 tests passed)** |
| `./venv/bin/ruff check app/services/section_vocabulary.py app/services/section_detector.py tests/test_section_detector.py` | **Passed (All checks passed)** |

### Refinements Applied during Audit:
- **Test Parameter Alignment:** Corrected expected section type for `"CONTACT"` to `"custom"` in `test_section_detector.py` since `"contact"` is not a valid `CVSectionType` in the schema.
- **Identity Leakage Prevention:** Enhanced structural heading detection so lines at the start of the CV (`index < 5`) matching candidate name, headline, or contact patterns are excluded. Extended name and headline stop words to include all canonical heading keywords (bilingual, accented/unaccented) so headers in short CVs are not falsely identified as part of the identity block.
- **Preceding Boundary Bug:** Fixed a logic asymmetry in `_looks_like_structural_heading` where preceding blank lines were not treated as separators, whereas succeeding ones were.
- **Skill Group Regex Expansion:** Relaxed `_SKILL_GROUP_RE` to support standard technical skills with mixed capitalization, numbers, and symbols (e.g., `FastAPI`, `C++`, `Node.js`, `SQL`).
- **Heading Title Preservation:** Updated boundary detection to set the display title of the section to the exact text matched from the CV (`stripped`) rather than the vocabulary variant, preserving original document casing.

## Acceptance criteria

- [x] Step 4.1 canonical vocabulary maps all known heading variants to
      canonical types (English + Vietnamese).
- [x] Step 4.2 combines vocabulary matching with structural signals (font
      size, capitalization, separator proximity, position) and does not
      classify headings by keyword alone.
- [x] Step 4.3 preserves unknown headings as `"custom"` sections and never
      drops unassigned content.
- [x] Every extracted line belongs to exactly one section or the identity
      preamble.
- [x] Identity preamble (name, headline, contact) extracted from top of document.
- [x] Summary section detected when present before the first recognized section.
- [x] Full test suite covering vocabulary, structural detection, identity,
      summary, boundaries, and end-to-end document construction.

## Remaining limitations

1. Structural heading detection is heuristic — very long headings (> 5 words)
   or headings without typographic emphasis (same font size as body) may be
   missed. These require LLM assistance (Phase 7).
2. The skill-group regex (`Label: item1, item2`) is English-centric. Vietnamese
   skill labels may need additional patterns.
3. Publication citation splitting (authors vs. title vs. venue) is not yet
   implemented — the full citation text goes into `publication.title`.
4. The detector is deterministic but conservative; it may under-segment
   documents with non-standard formatting. Phase 5 (section-specific parsers)
   will refine block typing within detected sections.

No commit was created as part of this implementation.
