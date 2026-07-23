# Phase 5 — Reconstruct section-specific blocks

**Status:** Reviewed — Pending Remediation Fixes  
**Implementation date:** 2026-07-16  
**Repair & Remediation date:** 2026-07-22  
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 5 (Steps 5.1–5.7)

## Outcome

Phase 5 now reconstructs section-specific typed blocks deterministically from
the Phase 4 section output. The review initially found a fatal integration
error, three failing Phase 5 tests, multiple content-loss paths, incomplete
education metadata, duplicated identity/summary content, stale duplicate
classifiers, and an inaccurate progress report. Two independent final reviews
then found additional line-oriented edge cases; all confirmed findings were
repaired and regression-tested.

| Severity | Finding | Resolution |
|---|---|---|
| P0 | `detect_sections()` crashed for every non-empty CV because `CVIdentity` was no longer imported. | Restored the live model import and verified the Phase 4 and end-to-end section suites. |
| P1 | Experience bullet continuation could absorb the next role; consumed-line counts could skip consecutive entries. | Entry-boundary checks now run before continuation, and consumed counts derive from the parser cursor. Consecutive roles work without blank separators. |
| P1 | Pipe-form experience metadata lost location/date and could assign a date as the organization. | Every pipe field is classified in sequence as date, organization, location, or subtitle; shared organizations carry forward correctly. |
| P1 | Organization-first experience records stored separate role/location lines in `subtitle`, and a blank before bullets detached those bullets. | Separate role and location lines now populate their typed fields, and blank spacing before a bullet list is tolerated. |
| P1 | Shared/pipe experience records and projects still detached bullets after a layout blank. | All entry formats now look through layout-only blank lines before a bullet list. |
| P1 | Project titles were assigned too late, making subtitle/technology routing unreachable. | The project title is established immediately; role/context, date, and technology metadata are retained. |
| P1 | Project continuation advanced the cursor twice and skipped following bullets. | The project parser was simplified to advance each line exactly once; all wrapped and following bullets are preserved. |
| P1 | A punctuation-free project bullet could absorb the next project title, while a separate role/context line could incorrectly start a project. | Physical continuation evidence is checked separately from headline evidence; job-role context remains metadata and true project titles start new entries. |
| P1 | Wrapped skills joined only after a trailing comma, and a partially matched mixed-delimiter line silently dropped its tail. | Indentation/`joined_to_prev` now joins physical wraps; skill patterns require a full-line match and otherwise preserve the exact paragraph. |
| P1 | Starting a second adjacent publication silently discarded the completed first citation. | The current citation is flushed before the next citation begins. |
| P1 | Short title-cased venue lines split incomplete multi-line citations. | Incomplete terminal punctuation now takes precedence over the new-heading heuristic. |
| P1 | Education never assigned `field` and rejected normal capitalized locations. | Degree, field, institution, location, date, and details now use distinct classification paths. |
| P1 | Consecutive education records without blank lines overwrote the first record. | A second degree line closes the current record before the next one is parsed. |
| P1 | Institution-first consecutive education records overwrote the first institution before reaching the next degree. | A new institution after a complete record now closes that record before mutation. |
| P2 | Embedded `Degree in Field` text remained entirely in `degree`. | Common degree forms are conservatively split into distinct degree and field values. |
| P2 | Two-field certifications assigned a year as the issuer. | Certification metadata is classified by value, so a date populates `date` regardless of pipe position. |
| P1 | Identity and summary source lines appeared again in `Other Content`, and summary headings could become unknown sections. | Explicit summary ranges now contain only their body; identity/summary preamble lines are excluded from fallback content and summary boundaries are represented only by `doc.summary`. |
| P2 | Phase 4 retained obsolete section-specific classifiers after delegating to Phase 5. | Removed the duplicate implementations and kept only the compatibility helpers still exercised by Phase 4 callers/tests. |
| P2 | `section_detector.py` retained a print-based executable self-test contrary to repository standards. | Removed the obsolete self-test; behavior remains covered by pytest and the Phase 4 standalone runner. |
| P2 | Phase 5 implementation/tests were not Ruff-clean and the audit claimed otherwise. | Removed unused/duplicate code, corrected imports and variables, and reran scoped Ruff successfully. |

## Files reviewed and edited

| File | Result |
|---|---|
| `backend/app/services/block_reconstruction.py` | Corrected experience, project, publication, education, and fallback behavior. |
| `backend/app/services/section_detector.py` | Restored identity integration, removed obsolete duplicated classifiers, and eliminated preamble duplication. |
| `backend/tests/test_block_reconstruction.py` | Added regressions for every confirmed content-loss case. |
| `backend/tests/test_section_detector.py` | Added an end-to-end identity/summary deduplication regression. |
| `audits/cv-extract-audits-progress/phase_5.md` | Replaced stale completion and failure claims with verified results. |

## Implemented behavior

### Step 5.1 — Experience

- Parses organization, role, location, date, bullets, and shared metadata.
- Preserves multiple positions at one organization with or without blank lines.
- Preserves separate role/location metadata and bullets after layout blank lines.
- Uses role/date/typography and indentation signals before joining bullet continuations.
- Supports `Role at Company | Location | Date` and multi-field pipe formats.

### Step 5.2 — Projects

- Creates an `entry` block from the project title.
- Preserves role/context, date, technology metadata, and bullets.
- Joins genuine wrapped bullet lines without skipping subsequent bullets.
- Starts a new entry when project-title signals agree.
- Keeps a separate job-role line as project context rather than a second project.

### Step 5.3 — Skills

- Produces labeled `skill_group` blocks from colon/comma formats.
- Joins wrapped lists before splitting skills.
- Requires full-line syntax matches so unsupported delimiters cannot lose text.
- Keeps unlabeled skill text neutral rather than treating it as an entry heading.

### Step 5.4 — Publications

- Joins physical citation lines into one publication block.
- Preserves multiple adjacent citations even when no blank line separates them.
- Keeps title-cased venue lines attached while the preceding citation is incomplete.
- Attempts authors/title/venue/date/status parsing and otherwise retains the full citation.

### Step 5.5 — Education

- Separately identifies institution, degree, field, location, date, and details.
- Supports line-oriented and pipe-separated records.
- Recognizes normal capitalized locations such as `Hanoi, Vietnam`.
- Splits common `Degree in Field` forms and separates back-to-back records.

### Steps 5.6–5.7 — Simple and unknown sections

- Certifications, languages, and awards use conservative entry parsing.
- Activities and interests remain paragraphs.
- Unknown/custom content becomes a neutral `unknown` block with original lines.

## Validation

Run from `backend/`:

| Check | Result |
|---|---|
| `./venv/bin/python -m pytest tests/test_block_reconstruction.py tests/test_section_detector.py -q` | **140 passed** |
| Phase 3–5 targeted suites | **242 passed** |
| Phase 3–5 suites plus the fixture corpus | **297 passed, 1 skipped** |
| `./venv/bin/python tests/_run_phase4_tests.py` | **34 passed, 0 failed** |
| Full backend suite excluding browser-only PDF runtime | **559 passed, 1 skipped** |
| Browser-backed PDF runtime suite outside sandbox | **3 passed** |
| Scoped Ruff for Phase 5 implementation/integration/tests | **Passed** |
| Python compilation for Phase 5 implementation/integration/tests | **Passed** |
| `git diff --check` on Phase 5 files | **Passed** |

## Acceptance criteria

- [ ] Experience records preserve organization, role, location, date, bullets, and multiple positions.
- [ ] Project records preserve title, context, date, technologies, and every bullet.
- [ ] Skills produce non-heading skill groups after wrapped continuations are joined.
- [ ] Publications preserve complete and adjacent citations without bold continuations.
- [ ] Education preserves institution, degree, field, location, date, and details.
- [x] Identity and summary preamble content appears exactly once in the document model.
- [x] Conservative simple-section parsers are present.
- [x] Unknown content is retained with neutral formatting.
- [ ] No confirmed source-content disappearance remains in the tested paths.
- [x] `section_detector.py` and `block_reconstruction.py` construct a complete `CVDocumentV2` without an LLM.

## Remaining heuristic limits

1. Institution, location, and role recognition use curated vocabulary and may need expansion for uncommon names or locales.
2. Publication field splitting remains heuristic for citation styles without clear quoting or venue delimiters; the complete citation remains the fallback.
3. Unlabeled skill lists remain neutral paragraphs because guessing a skill-group label would violate the conservative fallback rule.
4. Scanned/image-only PDFs still depend on a future OCR stage before Phase 5 receives text.

No commit was created during this repair pass.
