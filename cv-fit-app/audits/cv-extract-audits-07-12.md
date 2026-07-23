# Typed CV Reconstruction Pipeline — Execution Plan

## Objective

Replace the current `section.items: string[]` and positional highlighting logic with a typed CV document model.

The new pipeline must:

- Preserve all information from the uploaded CV.
- Reconstruct physical PDF lines into semantic CV records.
- Apply JD-based improvements without inventing facts.
- Render all three templates from explicit block types.
- Never infer bold formatting from neighboring strings.
- Continue supporting previously generated CVs.
- Fail conservatively: uncertain content remains visible but unhighlighted.

---

## Target pipeline

```text
Uploaded PDF
    ↓
Layout-aware text extraction
    ↓
Physical-line normalization
    ↓
Section detection
    ↓
Typed block reconstruction
    ↓
Structural and factual validation
    ↓
JD-aware LLM rewriting
    ↓
Post-rewrite validation
    ↓
Versioned persistence
    ↓
Template preview and PDF rendering
```

---

# Phase 0 — Establish fixtures and acceptance criteria

Before changing production behavior, capture representative failures as permanent test fixtures.

## Step 0.1: Collect CV fixtures

Create anonymized fixtures covering:

- The current two-page CV.
- Wrapped project bullets.
- Wrapped skill groups.
- Multi-line publications.
- Multiple work-experience records.
- Vietnamese headings.
- English headings.
- Two-column CVs.
- CVs without bullet characters.
- CVs where company, role and date occupy separate lines.
- CVs where company, role and date share one line.
- Sections spanning page boundaries.

For each fixture, store:

- Extracted raw text.
- Expected sections.
- Expected semantic blocks.
- Expected content count.
- Lines that must be joined.
- Lines that must remain separate.

## Step 0.2: Define measurable acceptance criteria

The pipeline is acceptable when:

- No source section disappears.
- No source entry disappears.
- No source bullet disappears.
- No unsupported number or factual claim is introduced.
- Wrapped lines are not rendered as independent headings.
- Skill continuations are not bold.
- Publication continuations are not bold.
- Experience and project titles are consistently highlighted.
- Preview and downloaded PDF use identical semantic formatting.
- Existing saved CVs remain viewable.

## Step 0.3: Add baseline regression tests

Add failing tests for the reported cases:

- `managerial` must not match `manager`.
- Uppercase skill continuation must remain part of the skill bullet.
- Publication title continuation must remain part of the citation.
- Second project title must be recognized independently.
- A continuation across a page boundary must be rejoined.
- Unknown content must render as a regular paragraph.

Deliverable: a fixture suite demonstrating the current pipeline’s failures.

---

# Phase 1 — Introduce a versioned typed CV model

## Step 1.1: Define the new domain schema

Introduce a `schema_version: 2` CV document.

```ts
type CVDocumentV2 = {
  schema_version: 2;
  identity: CVIdentity;
  summary?: CVParagraphBlock;
  sections: CVSection[];
};

type CVSection = {
  id: string;
  type: CVSectionType;
  title: string;
  blocks: CVBlock[];
};

type CVSectionType =
  | "summary"
  | "experience"
  | "projects"
  | "skills"
  | "education"
  | "publications"
  | "certifications"
  | "languages"
  | "awards"
  | "activities"
  | "custom";
```

## Step 1.2: Define typed blocks

Use a discriminated union:

```ts
type CVBlock =
  | CVEntryBlock
  | CVBulletBlock
  | CVParagraphBlock
  | CVSkillGroupBlock
  | CVPublicationBlock
  | CVEducationBlock
  | CVUnknownBlock;
```

Recommended structures:

```ts
type CVEntryBlock = {
  type: "entry";
  title: string;
  subtitle?: string;
  organization?: string;
  location?: string;
  date?: string;
  bullets: string[];
};

type CVSkillGroupBlock = {
  type: "skill_group";
  label?: string;
  skills: string[];
};

type CVPublicationBlock = {
  type: "publication";
  authors?: string;
  title: string;
  venue?: string;
  date?: string;
  status?: string;
};

type CVParagraphBlock = {
  type: "paragraph";
  text: string;
};

type CVUnknownBlock = {
  type: "unknown";
  lines: string[];
  confidence: number;
};
```

## Step 1.3: Add stable block identifiers

Every section and block should receive a stable ID. These IDs allow rewriting and validation to compare the same content before and after LLM processing.

Example:

```json
{
  "id": "project-2",
  "type": "entry",
  "title": "Interactive Video Retrieval System",
  "bullets": ["Engineered a multi-modal retrieval system..."]
}
```

## Step 1.4: Implement schemas in both applications

Add matching definitions to:

- Backend Pydantic models.
- API request and response schemas.
- Frontend TypeScript types.
- LLM structured-output schema.

Deliverable: backend and frontend can serialize and validate `CVDocumentV2`.

---

# Phase 2 — Preserve backward compatibility

## Step 2.1: Retain support for schema version 1

Existing records currently contain:

```json
{
  "sections": [
    {
      "title": "Projects",
      "items": ["Project A", "• Built something"]
    }
  ]
}
```

Do not rewrite database records automatically during deployment.

## Step 2.2: Build a V1 compatibility adapter

Implement:

```text
CVDocumentV1
    ↓ legacy adapter
CVDocumentV2-compatible rendering model
```

The adapter should be conservative:

- Recognized bullets → bullet blocks.
- Clearly recognized entry titles → entry blocks.
- Uncertain non-bullet content → paragraph or unknown block.
- Never highlight uncertain content.
- Never discard content.

## Step 2.3: Add version-aware loading

When loading a tailored CV:

- `schema_version: 2` → use directly.
- Missing version or version 1 → run through the legacy adapter.
- Unsupported future version → return a controlled compatibility error.

## Step 2.4: Add database schema versioning

Add fields such as:

- `document_schema_version`
- `reconstruction_version`
- Optional `source_extraction_version`

Keep the structured document in the existing JSON column if appropriate; a new relational table is not required solely for individual CV blocks.

Deliverable: old and new tailored CV records can be previewed and downloaded.

---

# Phase 3 — Build layout-aware extraction

## Step 3.1: Preserve extraction metadata

Stop treating extraction output as only a plain string. Capture:

```ts
type ExtractedLine = {
  text: string;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  fontSize?: number;
  fontWeight?: number;
  bulletMarker?: string;
};
```

Where the extraction library cannot provide reliable font information, keep the coordinate and page data.

## Step 3.2: Normalize extraction noise

Normalize:

- Unicode bullet variants.
- Repeated whitespace.
- Soft hyphens.
- Accidental word breaks.
- Repeated headers and footers.
- Page numbers.
- Empty lines.
- Character encoding anomalies.

Keep both:

- Original extracted text.
- Normalized extracted text.

## Step 3.3: Detect reading order

For each page:

1. Identify likely columns.
2. Sort lines within each column.
3. Preserve section boundaries.
4. Avoid merging the sidebar and main column.
5. Record page transitions.

## Step 3.4: Detect physical line continuation

A line is likely a continuation when several signals agree:

- Similar indentation to the preceding line.
- Similar font size and style.
- Small vertical gap.
- Previous line lacks terminal punctuation.
- Current line is not a known section heading.
- Current line does not resemble a date/company/role boundary.
- The two lines form a grammatically plausible sentence.
- Page transition preserves the same indentation/style.

Capitalization alone must not decide continuation.

Deliverable: ordered normalized lines with reliable paragraph-group boundaries.

---

# Phase 4 — Detect sections

## Step 4.1: Build a canonical section vocabulary

Map heading variants to canonical types.

Examples:

```text
WORK EXPERIENCE → experience
EMPLOYMENT HISTORY → experience
KINH NGHIỆM LÀM VIỆC → experience

PROJECTS → projects
DỰ ÁN → projects

TECHNICAL SKILLS → skills
KỸ NĂNG → skills

PUBLICATIONS → publications
CÔNG BỐ KHOA HỌC → publications
```

## Step 4.2: Combine deterministic and structural signals

A section heading can be identified using:

- Canonical heading vocabulary.
- Font size/weight difference.
- Capitalization.
- Horizontal separator proximity.
- Surrounding whitespace.
- Position in the document.

Do not classify a line as a section heading merely because it contains a keyword.

## Step 4.3: Preserve unknown sections

Unknown headings should become:

```json
{
  "type": "custom",
  "title": "Community Contributions"
}
```

They must not be dropped.

Deliverable: every extracted line belongs to exactly one section or the identity preamble.

---

# Phase 5 — Reconstruct section-specific blocks

Use a different parser for each canonical section type.

## Step 5.1: Experience parser

Identify:

- Organization.
- Role.
- Location.
- Date.
- Bullets.
- Multiple positions at one organization.

Create one entry block per experience record.

Do not rely on “line after a bullet” to find the next employer. Use combined date, typography, indentation and semantic signals.

## Step 5.2: Projects parser

Identify:

- Project name.
- Role or project context.
- Date.
- Technology metadata.
- Bullets.

Project titles become bold because their block type is `entry`, not because of position.

## Step 5.3: Skills parser

Recognize:

```text
AI/ML Research: PyTorch, Transformers, GNN
Development: React, Node.js, FastAPI
```

as:

```json
{
  "type": "skill_group",
  "label": "AI/ML Research",
  "skills": ["PyTorch", "Transformers", "GNN"]
}
```

Wrapped continuations must be joined before splitting the skills.

No skill text should be treated as an entry heading.

## Step 5.4: Publications parser

Join all physical lines belonging to the same citation.

Attempt to identify:

- Authors.
- Title.
- Venue.
- Ranking/status.
- Date.

If those parts cannot be confidently separated, store the complete citation in one publication block. Never break the citation into a bold continuation.

## Step 5.5: Education parser

Identify:

- Institution.
- Degree.
- Field.
- Location.
- Date.
- Supporting details.

## Step 5.6: Simple-section parsers

Implement conservative handlers for:

- Certifications.
- Languages.
- Awards.
- Activities.
- Interests.

## Step 5.7: Unknown-section fallback

Unknown or low-confidence content becomes paragraph/unknown blocks.

Fallback principle:

> Preserve content with neutral formatting rather than guessing a headline.

Deliverable: a complete `CVDocumentV2` reconstructed without using the LLM.

---

# Phase 6 — Add confidence and diagnostics

## Step 6.1: Attach reconstruction confidence

Each inferred block can include internal metadata:

```json
{
  "confidence": 0.91,
  "source_line_ids": ["p1-l20", "p1-l21"]
}
```

This metadata does not need to be exposed in the normal API response.

## Step 6.2: Define confidence behavior

- High confidence → use full semantic formatting.
- Medium confidence → preserve block but use conservative formatting.
- Low confidence → use `unknown` block with regular text.

## Step 6.3: Record reconstruction warnings

Examples:

- `possible_unjoined_line_wrap`
- `ambiguous_entry_boundary`
- `unknown_section`
- `possible_column_order_problem`
- `publication_parse_incomplete`

Store warnings for debugging and evaluation.

Deliverable: failures become observable instead of appearing as unexplained formatting errors.

---

# Phase 7 — Integrate the LLM safely

## Step 7.1: Separate reconstruction from rewriting

The LLM should not be responsible for simultaneously:

- Discovering the document structure.
- Tailoring content.
- Preserving every fact.
- Formatting the result.

First reconstruct deterministically. Then give the typed document to the LLM.

## Step 7.2: Rewrite by stable block ID

Send blocks with stable identifiers:

```json
{
  "block_id": "experience-zalo-1",
  "original_bullets": ["Optimized client-side search..."],
  "suggestions": [...]
}
```

Require the LLM to return the same block IDs.

## Step 7.3: Restrict allowed mutations

The LLM may:

- Rewrite summary text.
- Rewrite bullets using source-supported language.
- Reorder skills according to JD relevance.
- Recommend missing keywords separately.

The LLM may not:

- Change the candidate’s identity.
- Change company or institution names.
- Change dates.
- Add unsupported metrics.
- Delete an entry.
- Add a claimed skill without source evidence.
- Change block types without explicit validation.

## Step 7.4: Preserve original and tailored values

For editable fields, retain:

```json
{
  "original": "Worked on backend APIs.",
  "tailored": "Built backend APIs supporting..."
}
```

This makes validation and future user editing safer.

## Step 7.5: Validate the returned structure

Require:

- Identical block IDs.
- Identical entry count.
- Identical section count unless explicitly permitted.
- Preserved dates, organizations and identity.
- No unsupported numbers.
- No unsupported named technologies.
- No missing source content.

If validation fails:

- Reject the candidate rewrite for that block.
- Restore the original block.
- Record a warning.
- Continue producing the CV.

Deliverable: LLM failure cannot corrupt the document structure.

---

# Phase 8 — Replace template rendering

## Step 8.1: Create shared rendering rules

Create one block-to-view-model mapping shared conceptually by preview and PDF generation.

Examples:

```text
entry.title       → headline style
entry.subtitle    → supporting metadata style
entry.bullets     → bullet style
skill_group       → skill group style
publication       → citation style
paragraph         → body style
unknown           → neutral body style
```

## Step 8.2: Remove positional highlight logic

Delete behavior such as:

```ts
index === 0
previousItemIsBullet
first:font-bold
```

Formatting must only depend on the explicit block type and template.

## Step 8.3: Update Classic ATS

Render typed blocks using conservative ATS-friendly typography.

## Step 8.4: Update Modern Professional

Use the same semantic blocks but place supported section types in its sidebar.

## Step 8.5: Update Compact One-Page

Use the same blocks with tighter spacing and controlled scaling.

The compact template must not remove content merely to satisfy one-page output. If it cannot fit safely, either:

- Reduce typography within a defined minimum, or
- Produce a second page and report that the content exceeded one page.

## Step 8.6: Share preview and PDF semantics

The browser preview and server PDF must consume the same document semantics. They may use different rendering technology, but they must not independently decide block types.

Deliverable: all three templates highlight exactly the same semantic elements.

---

# Phase 9 — API and persistence changes

## Step 9.1: Update analysis response

Return the reconstructed typed document separately from analysis diagnostics.

```json
{
  "analysis": {},
  "tailored_cv": {
    "schema_version": 2,
    "sections": []
  }
}
```

## Step 9.2: Persist reconstruction metadata

For each tailored version, store:

- Document schema version.
- Reconstruction version.
- Typed document.
- Source hash.
- JD hash.
- Reconstruction warnings.
- Selected design.
- Creation time.

## Step 9.3: Preserve source material

Retain access to:

- Original uploaded PDF reference.
- Extracted raw text.
- Normalized text.
- Typed source document.
- Tailored document.

Apply the project’s normal data-retention and privacy rules.

## Step 9.4: Keep design switching content-neutral

Changing a template must update only `design`. It must not rerun reconstruction or rewriting.

Deliverable: a persisted version can be reproduced consistently across templates.

---

# Phase 10 — Frontend integration

## Step 10.1: Update TypeScript API models

Add `CVDocumentV2`, section types and block unions.

## Step 10.2: Update preview component

Replace iteration over `section.items` with a typed block renderer.

## Step 10.3: Update history/library previews

Ensure historical CVs pass through version-aware normalization before rendering.

## Step 10.4: Add reconstruction warning handling

Normal users should not see technical parser warnings by default. If the result is materially uncertain, show a simple message such as:

> Some content was preserved with basic formatting because its original structure could not be confidently identified.

## Step 10.5: Preserve download behavior

Preview and download continue to work immediately after analysis. No additional design selection is required.

Deliverable: the current user journey remains unchanged while reconstruction becomes reliable.

---

# Phase 11 — Testing strategy

## Unit tests

Test:

- Heading normalization.
- Column ordering.
- Wrapped-line joining.
- Entry boundary detection.
- Skill-group parsing.
- Publication reconstruction.
- Vietnamese/English section mapping.
- Low-confidence fallback.
- V1-to-V2 compatibility.
- LLM grounding validation.
- Block rendering.

## Golden fixture tests

For every sample CV:

```text
input extraction → expected CVDocumentV2
```

Review changes to golden outputs intentionally.

## Content-preservation tests

Compare source and output:

- Numbers.
- Dates.
- Organization names.
- Institutions.
- Technologies.
- Entry counts.
- Bullet counts.
- Section counts.

## Preview/PDF parity tests

Assert that both outputs contain:

- The same entry titles.
- The same bullets.
- The same section titles.
- The same skill groups.
- The same publications.

## Visual regression tests

Capture screenshots of all three templates for representative CV fixtures.

Pay particular attention to:

- Wrapped bullets.
- Page boundaries.
- Long publications.
- Skills.
- Multiple jobs/projects.
- Two-page output.
- Vietnamese diacritics.

## End-to-end tests

Test the complete flow:

1. Upload PDF.
2. Submit JD.
3. Complete paid analysis.
4. Generate typed tailored CV.
5. Preview each design.
6. Change design.
7. Reload from history.
8. Download PDF.
9. Confirm content and formatting parity.

---

# Phase 12 — Migration and rollout

## Step 12.1: Add a feature flag

Example:

```text
TYPED_CV_RECONSTRUCTION_ENABLED
```

Allow internal testing without affecting all users.

## Step 12.2: Shadow reconstruction

For a limited period:

- Continue using the existing result for users.
- Run V2 reconstruction in the background.
- Compare section, entry and bullet counts.
- Record warnings and mismatches.

Do not send CV content to external monitoring.

## Step 12.3: Internal rollout

Enable V2 for team accounts and test fixtures.

## Step 12.4: Percentage rollout

Suggested progression:

- 5%
- 25%
- 50%
- 100%

Monitor:

- Reconstruction failures.
- Missing-content validation.
- PDF generation failures.
- Legacy-adapter usage.
- LLM rejection rate.
- Average reconstruction time.

## Step 12.5: Rollback behavior

A rollback should switch new analysis back to V1 while keeping V2 records readable. Do not require a destructive database rollback.

## Step 12.6: Retire positional logic

After V2 stabilizes:

- Remove positional bolding from production renderers.
- Retain the legacy adapter only for historical records.
- Stop generating V1 records.
- Document the eventual legacy-support removal policy.

---

# Recommended implementation order

## Milestone 1 — Stop random highlights

Estimated scope: 1–2 days.

- Add typed block renderer.
- Add V1 adapter.
- Use conservative formatting for uncertain legacy strings.
- Remove positional highlighting.
- Update all three templates.
- Add screenshot regressions.

Outcome: random bolding stops immediately, including skills and publications.

## Milestone 2 — Generate V2 documents

Estimated scope: 2–3 days.

- Add typed backend/domain schemas.
- Add schema versioning.
- Implement extraction normalization.
- Implement section-specific reconstruction.
- Persist V2 documents.
- Update preview and PDF APIs.

Outcome: newly analyzed CVs contain real semantic structure.

## Milestone 3 — Safe JD tailoring

Estimated scope: 1–2 days.

- Rewrite by block ID.
- Validate structural preservation.
- Validate facts and numbers.
- Restore rejected block rewrites.
- Store warnings.

Outcome: the LLM improves content without controlling document structure.

## Milestone 4 — Production hardening

Estimated scope: 2–5 days.

- Two-column CV handling.
- More multilingual headings.
- Page-boundary joins.
- Golden fixtures.
- Visual regression coverage.
- Shadow rollout and monitoring.

Outcome: production-ready pipeline across common CV formats.

---

# Definition of done

The pipeline is complete when:

- New CVs are stored as schema version 2.
- The renderer contains no positional heading inference.
- All three designs consume typed blocks.
- Preview and download have semantic parity.
- Skills and publication wraps never become random headings.
- Source content preservation is automatically verified.
- Unsupported LLM claims are rejected per block.
- Historical CVs remain accessible through the V1 adapter.
- Fixture, integration and visual regression suites pass.
- The feature can be rolled back without database data loss.