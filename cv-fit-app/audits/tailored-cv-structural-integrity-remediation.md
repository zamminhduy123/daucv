# Tailored CV Structural Integrity — Remediation Decision Map

## Objective

Make the Tailored CV pipeline preserve the source CV's record boundaries and
facts while allowing only Grounded Rewrites. The source PDF is the authority;
the Tailored CV must never merge employers, duplicate publications, collapse
degrees, drop records, or introduce unsupported claims.

## Evidence baseline

Private local acceptance artifacts (do not commit):

- `/Users/rzy/Desktop/sch/CV/CV_DUYNGUYEN_2pu.pdf` — Source CV, two-page Letter PDF.
- `/Users/rzy/Desktop/sch/CV/Principal-AI-Native-Architect-Koidra.pdf` — failing Tailored CV, two-page A4 PDF.

Confirmed failures in the tailored artifact:

- Soonchunhyang research and Zalo employment are merged into one work record.
- The Zalo record is flattened into pipe-separated prose.
- Publications repeat citation content and metadata.
- Two education records and certifications are collapsed into one paragraph.
- Claims such as `100% uptime`, `eliminate server costs`, `MCP`, and `LangGraph`
  require source provenance and must be rejected when unsupported.

The current deterministic reconstruction now recovers seven sections, two
education records, three projects, the research appointment, and the Zalo
employment record. The fixes remain incomplete:

- section classification still depends on exact normalized aliases, including
  aliases added directly from this CV;
- unknown headings are only preserved when conservative typography heuristics
  recognize them, so a weakly formatted heading can still be swallowed by the
  preceding section;
- the upload-analysis path can reconstruct from layout metadata, while the
  Tailored CV path reconstructs again from plain text and ignores a different
  client-provided Source Document;
- education, project, and experience metadata are still overloaded or missing;
- publication blocks store a full citation in `title` and repeat parts in
  `authors`, `venue`, and `date`;
- some extracted lines lose spaces, such as `Achievedstate...` and
  `Builtamultimodal...`.

## Reconstruction architecture principles

- Canonical section types are a closed ontology; user-authored heading text is
  open vocabulary.
- Exact heading aliases are high-confidence fast paths, not the only way to
  establish a section boundary.
- Boundary detection and semantic classification are separate decisions. A
  line can be a definite heading while its canonical type remains uncertain.
- Layout and document structure establish boundaries before vocabulary is used
  to assign a canonical type.
- Ambiguous headings remain distinct `custom` sections. They are never merged
  into the previous section and are not eligible for unconstrained rewriting.
- Reconstruction occurs once from the richest available source representation.
  The stored, versioned Source Document is reused by analysis, tailoring,
  persistence, preview, and export; downstream stages never reconstruct it from
  plain text.
- Every normalized source line has exactly one owner or an explicit documented
  exclusion. Content conservation is more important than forcing every section
  into a canonical category.

## Non-negotiable acceptance contract

- Every source section remains present exactly once unless an explicit product
  rule says it is intentionally omitted.
- Every employer, research appointment, project, degree, certification, and
  publication remains a distinct record with the correct owning section.
- Identity, organizations, titles, dates, credentials, URLs, numbers, and
  publication metadata are immutable during tailoring.
- A Grounded Rewrite may change only approved prose fields and must retain the
  source block ID and source-line provenance.
- Unsupported changes are rejected per block; rejected content falls back to
  the corresponding source block, never to a different record.
- Preview and downloaded PDF render the same typed document in the same semantic
  order.
- The real private CV is an acceptance artifact only. A redacted structural
  equivalent is committed as the permanent regression fixture.
- Completion is reported as `VERIFIED` only after the real source-to-PDF flow
  passes. Unit-only or mocked checks are `MOCK_VERIFIED`; missing external
  runtime evidence is `BLOCKED`.

## #1: Capture a reproducible stage-by-stage failure trace

Blocked by: none
Type: Research

### Question

At which exact pipeline stage does each observed corruption first appear?

### Answer

Create a local diagnostic run for the two supplied PDFs and persist sanitized
stage snapshots under a temporary or ignored path:

1. physical extraction lines with coordinates and font metadata;
2. normalized logical lines and continuation decisions;
3. detected section boundaries;
4. Reconstructed Source Document;
5. LLM rewrite request and response with sensitive content redacted from logs;
6. post-rewrite validated Tailored Document;
7. persistence payload and reloaded version;
8. preview semantic DOM and final PDF text/order.

For every bad output, record the earliest bad stage and the source line IDs.
Do not begin broad fixes until the first divergence is identified for each
failure category.

Deliverable: `audits/artifacts/tailored-cv-trace-summary.md` containing only
sanitized structure, counts, warnings, and first-divergence findings.

Exit gate: every visible PDF defect has one named first-divergence stage.

## #2: Build the source-to-output oracle

Blocked by: #1
Type: Discuss

### Question

What exact structure and facts must the pipeline preserve for this CV?

### Answer

Create a human-reviewed oracle for the Source CV with stable semantic IDs and
expected ownership:

- identity and contact links;
- Professional Summary;
- two education records;
- six technical-skill groups;
- one research appointment with eight bullets;
- three Applied AI Projects with their own metadata and bullets;
- one Zalo employment record with seven bullets;
- two publications;
- two certifications.

For each record, capture organization/title/date/location and the ordered source
line IDs. Mark fields as immutable facts or rewriteable prose. Add an explicit
deny-list of observed unsupported claims for the current regression.

Deliverables:

- private local oracle for the real CV;
- committed redacted fixture with the same structural hazards;
- machine-readable expected counts and parent-child ownership.

Exit gate: a human can compare any pipeline stage to the oracle without reading
renderer code.

## #3: Repair physical extraction and logical-line normalization

Blocked by: #1, #2
Type: Prototype

### Question

Can the extractor preserve spaces, reading order, line boundaries, and source
provenance for the Source CV before semantic parsing begins?

### Answer

Add the real PDF as a local-only acceptance case and reproduce the missing-space
examples. Correct word clustering and space insertion using bounding-box gaps,
font metrics, and original character order. Do not solve missing spaces with a
dictionary or language model.

Add regressions for:

- normal inter-word gaps versus intentionally joined glyphs;
- wrapped bullets across physical lines;
- page transitions;
- dash/bullet normalization;
- Letter and A4 input sizes;
- no line duplication or loss.

Exit gate: normalized text has exact readable words and every non-artifact source
line maps to one logical line or a documented continuation.

## #4: Generalize section boundary detection and canonical ownership

Blocked by: #3
Type: Prototype

### Question

Can arbitrary user-authored headings establish safe section boundaries without
requiring a new exact keyword for every CV?

### Answer

Replace exact-alias-first boundary detection with a staged classifier:

1. **Boundary candidate detection:** score layout signals independently of
   vocabulary: font-size/weight change, indentation, surrounding whitespace,
   separators, capitalization, line length, repeated visual style, and
   transition into entry-shaped content. Avoid a universal five-word cutoff.
2. **High-confidence canonical aliases:** retain normalized common English and
   Vietnamese aliases as deterministic fast paths.
3. **Compositional mapping:** classify heading nuclei and modifiers rather than
   complete phrases. For example, `Research` + `Experience`, `Engineering` +
   `History`, and `Relevant` + `Employment` can map to `experience`; `Selected`
   + `Projects` and `AI` + `Portfolio` can map to `projects`.
4. **Body-shape corroboration:** use entry patterns, dates, institutions,
   citations, skill labels, and bullets to support or reject a proposed type.
   Body shape must not manufacture a boundary on its own.
5. **Safe ambiguity:** preserve an uncertain but structurally strong heading as
   `custom` with its own lines, confidence, candidate types, and warnings.

Do not use unrestricted fuzzy string matching: a nearby spelling is not enough
to distinguish `Career Highlights`, a job title, and an organization name. If a
constrained LLM/embedding classifier is later evaluated, it may classify only
already-detected heading candidates, must return the closed ontology with a
confidence score, and must fall back to `custom`; it must never decide line
ownership or rewrite content.

Build a redacted heading corpus containing:

- at least 20 English and Vietnamese variants for each common canonical type;
- headings absent from the alias table (`Selected Engagements`, `What I Built`,
  `Academic Background`, and similar examples);
- long headings, mixed case, missing font metadata, and plain-text inputs;
- negative examples including names, organizations, roles, project titles,
  bullet subtitles, and short body lines;
- multi-column and page-transition cases.

Tests must assert boundary existence separately from canonical classification.
Assert 100% source-line ownership, zero duplicate ownership, stable section
order, and safe `custom` fallback for every ambiguous case.

Exit gate: all oracle sections remain distinct; the redacted corpus has no
swallowed content and no false boundary in its negative set; exact aliases are
not required for structural preservation.

## #5: Repair education, experience, project, publication, and certification blocks

Blocked by: #4
Type: Prototype

### Question

Can section-specific parsers reconstruct every independent record without
merging, duplication, or field overloading?

### Answer

Fix one parser at a time against the oracle:

- Education: close the SCH record before starting HCM VNU; bind each degree,
  institution, location, date, GPA, and focus detail to its own record.
- Experience: distinguish organization, role, location, date, and bullets;
  never carry organization metadata across unrelated employers.
- Projects: start a new entry at each project title; preserve role/context,
  dates, and every bullet.
- Publications: choose one canonical representation. Parsed fields may not also
  remain duplicated inside `title`; preserve the full source citation separately
  only if the model explicitly supports it.
- Certifications: preserve each issuer, credential, and date as a distinct
  record rather than a generic combined paragraph.

For every parser, assert record count, source-line coverage, field ownership,
ordering, and zero duplicated normalized text.

Exit gate: the Reconstructed Source Document matches the full oracle before any
LLM request is allowed.

## #6: Establish one authoritative Source Document and make it a hard gate

Blocked by: #5
Type: Discuss

### Question

How do all downstream stages reuse the same layout-aware reconstruction, and
what happens when that reconstruction is incomplete or low-confidence?

### Answer

Reconstruct once during upload from layout-aware `ExtractedLine` data. Persist
the Source Document, source hash, reconstruction version, layout provenance,
and diagnostics together. Analysis and tailoring requests reference that saved
artifact by server-owned ID/version; they must not rebuild it from `cv_text` or
trust a client-supplied replacement.

Remove the current split where analysis may call `reconstruct_from_lines()` but
Tailored CV persistence calls `reconstruct_cv_text()` and reports
`client_source_document_ignored`. Define an explicit compatibility path for old
records without a saved V2 artifact: reconstruct once, label it as migrated,
run the same gate, and persist it before tailoring.

Do not tailor structurally unsafe documents. The reconstruction gate checks:

- no known-section fallback to a single `unknown` block;
- no duplicate source-line ownership;
- no orphaned content lines;
- expected record boundaries are internally consistent;
- block confidence meets the required threshold for mutable block types;
- critical warnings are absent.

If the gate fails, return a controlled analysis result that explains the CV
could not be safely reconstructed and preserves the user's credit according to
the existing failure policy. Never silently continue through the legacy
free-form Tailored CV path.

Exit gate: a request cannot produce two Source Documents for the same source
hash and reconstruction version, and structurally unsafe inputs cannot reach
LLM rewriting or Tailored CV persistence.

## #7: Prove Grounded Rewrite safety and eliminate the legacy authority split

Blocked by: #6
Type: Prototype

### Question

Is there exactly one authoritative Tailored Document, and can the LLM modify
only source-backed prose?

### Answer

Trace the live API path and remove ambiguity between `legacy_tailored_cv`,
`document_v2`, `source_document_v2`, and the saved rendering document. The
server-owned Source Document established in #6 plus validated block rewrites
must be the sole authority for new V2 previews and PDFs.

Enforce:

- structural equality between source and tailored documents for immutable
  fields and parent-child relationships;
- exact block-ID membership;
- source-supported numbers, technologies, entities, credentials, and claims;
- no mutation of organization/title/date/publication/education metadata;
- no claims derived only from the JD;
- no fallback to an unconstrained LLM-generated document.

Add negative regressions for `100% uptime`, `eliminate server costs`, `MCP`, and
`LangGraph` when absent from the Source CV, plus positive cases for genuine
source metrics such as `95%`, `30%`, and `15+`.

Exit gate: malicious or accidental unsupported rewrites are rejected while safe
rewrites remain usable.

## #8: Verify API, persistence, and replay identity

Blocked by: #7
Type: Prototype

### Question

Does the document validated during analysis remain byte-for-byte structurally
equivalent after save, reload, design switching, and download?

### Answer

Add an end-to-end contract test covering:

1. PDF extraction;
2. analysis envelope;
3. one-time Tailoring Entitlement;
4. Tailored CV Version creation;
5. database reload;
6. design switch;
7. preview and PDF download.

Compare source hashes, reconstruction versions, block IDs, immutable fields,
record ownership, and tailored values at every boundary. Server-side replay
must use the stored authoritative source artifact and must not produce a
different reconstruction from the analysis stage.

Exit gate: save/reload/design operations cannot change content or structure.

## #9: Repair renderer semantics and visual parity

Blocked by: #8
Type: Prototype

### Question

Can all CV Designs render the verified Tailored Document without duplicating,
flattening, clipping, or reordering content?

### Answer

Test each block renderer independently and all three designs end to end.
Publication rendering must not concatenate a full citation with repeated parsed
metadata. Entry rendering must keep organization, role, location, date, and
bullets visually grouped. Education and certification entries must remain
separate.

Verify both semantic and visual parity:

- canonical DOM sequence and normalized text counts;
- no duplicate normalized sentences;
- page render screenshots at fixed browser/DPI settings;
- no clipping, overlap, stranded headings, or malformed page breaks;
- preview and server PDF contain identical semantic content.

Exit gate: all three designs pass semantic parity, and the chosen design passes
human visual review on both pages of the private real-CV acceptance run.

## #10: Run the final real-CV acceptance and rollout gate

Blocked by: #9
Type: Research

### Question

Is the repaired pipeline safe to call complete and deploy?

### Answer

Regenerate the Koidra Tailored CV from the original private Source CV and JD.
Produce a final source-to-output audit with:

- section and record counts;
- source-line coverage;
- grounded versus rejected rewrites;
- immutable field comparison;
- normalized duplicate detection;
- preview/PDF semantic comparison;
- page screenshots;
- all warnings and confidence scores.

Review every changed sentence manually for truthfulness and role relevance.
Run the full backend suite, frontend type-check/lint/build, database-backed
integration tests, and browser-backed PDF tests. Keep environmental failures
separate from application failures.

Exit gate: mark the work `VERIFIED` only when the regenerated real artifact has
zero merged records, zero dropped records, zero duplicated content, zero
unsupported claims, and zero visual defects. Otherwise return to the earliest
failed ticket.

## Execution order

```text
#1 trace → #2 oracle → #3 extraction → #4 generalized sections → #5 blocks
                                                           ↓
#10 acceptance ← #9 rendering ← #8 persistence ← #7 rewrite safety ← #6 authority + gate
```

## Recommended implementation slices

Each slice should be independently reviewable and should not mix formatting
cleanup with behavioral changes:

1. diagnostic trace and redacted oracle fixtures;
2. extraction-space regressions and fix;
3. open-vocabulary boundary corpus and generalized section detector;
4. education reconstruction regressions and fix;
5. experience/project reconstruction regressions and fix;
6. publication/certification reconstruction and rendering fix;
7. stored authoritative Source Document and reconstruction hard gate;
8. single-authority rewrite/API/persistence contract;
9. preview/PDF parity and real-artifact acceptance report.

Do not commit the two private PDFs. Commit only anonymized fixtures, expected
structural manifests, tests, code, and sanitized audit results.
