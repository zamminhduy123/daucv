# Phase 8 — Typed template rendering

**Status:** Completed and reviewed (uncommitted)  
**Implementation date:** 2026-07-16  
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 8 (Steps 8.1–8.6)

## Outcome

Classic ATS, Modern Professional, and Compact One-Page now render from explicit
typed blocks in both browser preview and server PDF generation. Positional
highlighting has been removed. Legacy V1 records first pass through the
conservative V1-to-V2 adapter.

## Implemented behavior

- Formatting depends on `entry`, `bullet`, `paragraph`, `skill_group`,
  `publication`, `education`, or `unknown`, never array position.
- Medium-confidence inferred blocks use neutral typography and unknown content is
  always visible as ordinary text.
- Modern Professional moves only explicit skills and education sections into its
  sidebar; it does not reclassify content.
- Compact One-Page uses a defined minimum typography and paginates instead of
  clipping. Long content receives the
  `compact_template_content_exceeds_one_page` diagnostic.
- Preview and PDF share a parity fixture that executes both renderers and compares
  canonical semantic DOM order, classes, data attributes, content, style tokens,
  and compact-overflow reporting across all three designs.

## Validation

- Typed renderer and legacy-adapter tests pass.
- Browser/PDF semantic parity contract: **4 passed**.
- Browser-backed PDF runtime tests confirm content is retained across pages.
- Frontend TypeScript and scoped ESLint pass.
- Full backend suite, including browser PDF tests: **553 passed, 1 skipped**.
- Production Next.js build completes successfully.

## Acceptance criteria

- [x] All templates use the same explicit block semantics.
- [x] No positional highlight logic remains in the production preview/PDF path.
- [x] Unknown and uncertain content stays visible and unhighlighted.
- [x] Compact rendering does not remove content and reports expected pagination.
- [x] Preview and PDF parity is regression-tested.

No commit was created.
