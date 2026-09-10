# CV Fit

CV Fit helps candidates assess a CV against a job description and create a truthful, job-targeted version of that CV.

## Language

**Tailored CV**:
A new, ATS-first CV generated automatically in the source CV's language from that CV and a specific job description, incorporating only truthful changes.
_Avoid_: Updated PDF, rewritten file

**CV Design**:
A user-selectable visual presentation applied when a Tailored CV is exported, without changing its content. The designs are Classic ATS and Compact; Classic ATS is the default. Both are single-column and ATS-safe (the two-column Modern Professional design was retired for poor ATS parsing; old records requesting it resolve to Classic ATS).
_Avoid_: Template, PDF layout

**Grounded Rewrite**:
A rewrite that improves wording, ordering, or JD relevance while being fully supported by the source CV; it introduces no unverified metrics, facts, or qualifications.
_Avoid_: Enhancement, suggestion

**Reconstructed Source Document**:
The typed, immutable representation of the Source CV used as the structural and factual authority for tailoring. Every reconstructed block retains provenance to source lines.
_Avoid_: Parsed draft, generated CV

**Structural Integrity**:
The guarantee that tailoring preserves the identity, section ownership, record boundaries, dates, organizations, credentials, publications, and source-backed content of the Reconstructed Source Document.
_Avoid_: Similar structure, best-effort layout

**Source Section**:
A recognized content area from the source CV, such as experience, projects, education, certifications, languages, awards, or volunteering. A Tailored CV retains each supported Source Section rather than reducing the candidate to a fixed set of sections.
_Avoid_: Optional block, filler section

**Candidate Identity**:
The contact details and URLs present in a source CV. A Tailored CV copies them exactly and does not add a photo.
_Avoid_: Profile data, contact enhancement

**CV Review & Workspace Editor**:
The three-part workspace (`/app/review`) where candidates inspect, edit, and curate their Reconstructed Source Document before analysis and tailoring. Features structured field editors (Identity, Experience, Education, Skills, Publications, Projects, Summary), per-section and global draft saving, and a unified top toolbar with section selection and typography tools.
_Avoid_: Static preview page, generic form builder

**CV Preview**:
The browser-rendered representation of a CV in its selected CV Design. Rendered via a lightweight, isolated iframe with continuous natural scrolling, dynamic scale-to-fit, and zero double scrollbars.
_Avoid_: Static PDF embed, external viewer modal

**Continuous Pagination & Page Breaks**:
The client-side DOM layout engine (`applyPageBreaks()`) inside the CV Preview iframe that dynamically measures elements against standard A4 page heights (1123px / 297mm). It automatically inserts an edge-to-edge separation band (`[ Trang N ]`), preserves whitespace, and protects section headings from being awkwardly orphaned at page bottoms.
_Avoid_: Rigid canvas pagination buttons, arbitrary CSS page breaks

**CV Typography & Spacing Engine**:
The real-time styling subsystem in `cv-render-html.ts` allowing granular document formatting without server roundtrips:
- **Proportional Base Scaling**: Base font size (`baseFontSize` in pt, default `9.5pt` Harvard/LaTeX standard) that scales Candidate Name (H1 ~2.1x), Headings (H2 ~1.2x), and body text proportionally to maintain ATS and typographic hierarchy.
- **Granular Spacing Hierarchy**: Section Gap (`sectionSpacing`), Item Gap (`itemSpacing`), Line Height (`lineHeight`), and Page Margin (`pageMargin`), all supporting minimum values down to `0` for precise 1-page CV budgeting.
- **Spacing Popover**: Floating panel on the sub-toolbar with interactive range sliders, precision `[-]` / `[+]` steppers, and a one-click reset to Harvard defaults.

**Tailoring Flow**:
The user starts a Tailored CV with “Tạo CV đã tối ưu”, selects a CV Design, views the CV Preview, and then downloads the PDF.
_Avoid_: Print analysis, edit-and-export flow

**Tailored CV Library**:
The Lịch sử area that lists a user's saved Tailored CV Versions and lets them reopen, change design, preview, download, or delete them without changing the source CV.
_Avoid_: Analysis history, temporary cache

**Tailored CV Version**:
A saved, user-owned instance of a Tailored CV associated with its source CV, target job description, and selected CV Design. It stores structured content and metadata, not a PDF binary; it is named from the target role and company extracted from the job description, with a dated fallback name; choosing another design updates this same version rather than creating a duplicate.
_Avoid_: Draft, cached result

**Tailoring Entitlement**:
The included right to create the first Tailored CV Version from one paid CV/JD analysis; it does not charge again for CV Design changes or downloads.
_Avoid_: Export credit, download credit

**Fast Document Hydration & Cache Strategy**:
The zero-latency loading architecture for `/app/review`:
- **Client Cache**: SessionStorage document cache (`document-cache.ts`) keyed by user and CV ID that hydrates `CVDocumentV2` synchronously in 0ms when navigating between workspace views.
- **Backend Auto-Persist**: `/api/cv/prefill` directly saves ground-truth structured documents to `user_cvs.structured_document` on creation, turning subsequent opens into 30ms single-query hits.
- **Pre-warming**: Deterministic prefill executes immediately upon file upload in `/app/setup`, eliminating the perceived preparation delay before opening the review wizard.
- **Progressive ReviewSkeleton**: Geometry-matching skeleton UI replacing static spinners for seamless first-load transitions.

