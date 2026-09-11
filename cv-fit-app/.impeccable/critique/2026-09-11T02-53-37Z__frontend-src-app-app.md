---
target: Judge the UI of our flow
total_score: 21
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/rzy/Desktop/ProjectWithTien/cv-helper/cv-fit-app/frontend/src/app/app"
timestamp: 2026-09-11T02-53-37Z
slug: frontend-src-app-app
---
# Critique — CV Fit workspace flow (frontend/src/app/app)

Method: dual-agent (design review + detector scan). Target slug: frontend-src-app-app.
Design Health Score: 21/40 (Acceptable). All 10 heuristics scored.

## Heuristic scores
1 Visibility of System Status: 2 — analyzer auto-run is a black box (indeterminate progress, no step count).
2 Match Real World: 3 — strong Vietnamese library metaphor; docked for leaked system terms (Giao diện, Giãn cách, credit economics unexplained).
3 User Control/Freedom: 2 — deletes are one-shot native confirms with no undo; guards force flow with silent replaces.
4 Consistency/Standards: 2 — two greens, gradient vs flat primaries, EN/VI mix, duplicated typography toolbars.
5 Error Prevention: 2 — good upload/JD gates; undermined by whole-card clickable div with nested delete on stopPropagation.
6 Recognition over Recall: 1 — no step indicator; sections hidden in dropdown; JD pill truncated; design rides silently via handoff.
7 Flexibility/Efficiency: 2 — steppers/sliders good; single-step diff carousel slow, no shortcuts.
8 Aesthetic/Minimalism: 2 — double toolbars + double save buttons in review; export triples the same info.
9 Error Recovery: 2 — retries exist; stale-doc 422 redirects away; no draft history.
10 Help/Documentation: 1 — only in-situ tips; no onboarding, scoring explainer, or credit explainer.

## Design specificity: borderline interchangeable (60/40)
Authored signals: #2D7A58 system, Vietnamese microcopy, forced JD-PDF gate, truthfulness UI (missing-contact notes, keyword warning, export subtitle). Category-generic: copy-pasted typography toolbars across review/export, gradient CTA row, English pipeline dashboard dropped into a Vietnamese app. Missed: 1-page obsession surfacing, mascot beyond loading, JD-requirement traceability for each diff.

## Detector (deterministic scan, exit 2, 2 findings, both likely false positives)
- gray-on-color layout.tsx:212 and setup/page.tsx:298 — both are text-gray-400 with hover-only bg-red-50 (text goes dark red on hover); steady state never renders gray-on-red.
- Browser visualization unavailable in harness (no browser tool); static evidence only, no overlays claimed.

## Priority issues
P1 Wayfinding for forced 4-step flow (Setup→Review→Analyzer→Export enforced, never visualized; sidebar collapses to one item).
P1 Destructive deletes via native confirm, no undo, trash 8px from open target.
P1 Screen-reader/keyboard gaps (CvCard div-onClick, duplicate iframe titles, color-only diffs, no focus trap, no live regions).
P2 Review double-toolbar + double-save overload.
P2 Analyzer triple CTA with inverted visual weight (gradient jobs link outranks tailor/save).
P2 Export default triples info (diff list + two full iframes, double render cost).

## Persona red flags
Jordan: auto-opened modal skips library mental model; 4 indistinguishable feature tiles; JD paste rejected without rationale; analysis auto-starts with no cost preview.
Sam:card not focusable; decorative thumbs announce filenames; sliders lack valuetext; modals lack focus management.
Casey: 794px preview scaled to ~340px unreadable; 28px steppers under thumb target; JD context hidden on mobile (TopBar hidden md:flex); backgrounded browser loses handoff → paid re-analysis.

## Minor observations
EN/VI split in pipeline dashboard; hardcoded CV_NTMDuy.pdf fallback filename; relative-time breaks past 24h; terminology drift (Giao diện/Chọn mẫu CV/Dùng tính năng); history icon tint mismatch; anchor.click() without DOM append; print CSS misses overlays; two diff UIs to learn.

## Questions to consider
- If the promise is grounded tailoring, why does export show what changed but never which JD line caused it?
- The JD-PDF mandate rejects the most common real JD (copied LinkedIn text) — parsing constraint masquerading as design?
- Review and export share one typography engine with the same visual weight, but one edits source truth and the other export presentation — does the product know which changed?
