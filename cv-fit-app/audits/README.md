# CVFit System Audits & Technical Integrity Documentation

This directory contains the central repository of engineering audits, architectural remediation blueprints, execution milestone progress logs, and safety gates established for the CVFit application.

---

## Directory Index

```
audits/
├── README.md                                          # Central index and documentation (this file)
├── security-audit-plan.md                             # Security vulnerability tracker & fix log
├── active-cv-review-2026-07-08.md                     # Active CV persistence & profile architecture review
├── uncommitted-review-2026-07-08.md                   # Working-tree security & code quality review
├── tailored-cv-structural-integrity-remediation.md    # Source PDF structural integrity & zero-hallucination blueprint
├── cv-extract-audits-07-12.md                         # 10-Phase execution plan for typed CV reconstruction
├── cv-extract-audits-progress/                        # Phase-by-phase implementation verification logs
│   ├── phase_0.md                                     # Phase 0: Acceptance fixtures & baseline
│   ├── phase_1.md                                     # Phase 1: Physical line normalization
│   ├── phase_2.md                                     # Phase 2: Section detector & aliases
│   ├── phase_2_review.md                              # Phase 2: Boundary classification review
│   ├── phase_3.md                                     # Phase 3: Typed block reconstruction
│   ├── phase_4.md                                     # Phase 4: Structural & factual validation gates
│   ├── phase_5.md                                     # Phase 5: Evidence-constrained LLM rewriter
│   ├── phase_6.md                                     # Phase 6: Post-rewrite verification
│   ├── phase_7.md                                     # Phase 7: Deterministic export & rendering parity
│   ├── phase_8.md                                     # Phase 8: Multi-template rendering
│   └── phase_9.md                                     # Phase 9: Versioned persistence & API envelopes
└── artifacts/                                         # Diagnostic traces & failure repro logs
    └── tailored-cv-trace-summary.md                   # First-divergence failure stage mapping
```

---

## 1. Security & Infrastructure Audits

### [`security-audit-plan.md`](./security-audit-plan.md)
* **Objective**: Identify and remediate security vulnerabilities across backend APIs, authentication, storage, and worker queues.
* **Key Remediations**:
  - **PII Masking**: Integrated `app/utils/pii_sanitizer.py` with custom regex to scrub emails, phone numbers, Vietnamese national IDs (CCCD/CMT), and IPv4 addresses before writing structured logs.
  - **CORS Hardening**: Replaced wildcard origins (`*`) with environment-configured `CORS_ALLOWED_ORIGINS` to satisfy secure credential-sharing requirements.
  - **OOM Protection**: Enforced strict `PDF_MAX_SIZE` (10 MB default) limits on all multipart upload endpoints before buffering or parsing in memory.
  - **Cryptographic Entitlement**: Enforced signed HMAC-SHA256 source tickets with nonces and short TTLs to prevent replayed or forged tailoring saves.

### [`uncommitted-review-2026-07-08.md`](./uncommitted-review-2026-07-08.md) & [`active-cv-review-2026-07-08.md`](./active-cv-review-2026-07-08.md)
* **Objective**: Guard against architectural anti-patterns, unauthorized route logic in routers, and insecure development fallbacks.
* **Standards Enforced**:
  - Thin route handlers: Database transactions and raw SQL moved out of routers into dedicated service modules (`user_cv_service.py`, `cv_pipeline_persistence_service.py`).
  - Strict typing: Return types required on all FastAPI dependency and handler functions.
  - Fail-fast environment requirements: Hard errors if `NEXTAUTH_SECRET` is unconfigured.

---

## 2. Typed CV Reconstruction & Zero-Hallucination Pipeline

### [`tailored-cv-structural-integrity-remediation.md`](./tailored-cv-structural-integrity-remediation.md)
* **Objective**: Eliminate LLM record hallucinations, merged work histories, dropped degrees, or fabricated metrics.
* **Core Principles**:
  1. **Source Authority**: The uploaded raw PDF/text is the immutable source of truth.
  2. **Closed Canonical Ontology vs. Open Vocabulary**: Section boundaries and block kinds are mapped deterministically to typed models (`CVDocumentV2`).
  3. **Zero Factual Invention**: LLMs are prohibited from introducing metrics, tools, seniority, or dates not grounded in the source document.
  4. **Strict Numeric Invariant**: All numbers/percentages in rewritten text must match the original evidence exactly.

### [`cv-extract-audits-07-12.md`](./cv-extract-audits-07-12.md) & `cv-extract-audits-progress/`
10-Phase roadmap transitioning CVFit from untyped string slices to an end-to-end typed, auditable document engine:
* **Phase 0–1**: Fixture collection and physical bounding-box line normalization (`phase_0.md`, `phase_1.md`).
* **Phase 2–3**: Dynamic section detection and semantic block reconstruction (`phase_2.md`, `phase_3.md`).
* **Phase 4–6**: Hard reconstruction quality gates, evidence bundling, and post-rewrite verification (`phase_4.md`, `phase_5.md`, `phase_6.md`).
* **Phase 7–9**: Multi-template PDF rendering parity (`phase_7.md`, `phase_8.md`) and versioned persistence with migration guards (`phase_9.md`).

---

## 3. Decoupled 3-Pipeline LLM Architecture

The current pipeline decouples the legacy monolithic `/api/analyze-cv` route into three distinct, single-responsibility LLM components with independent endpoints:

```
[Raw CV (PDF/Text)]
        │
        ▼ (LLM #1: CV Structuring & Range Plan Mapper)
[POST /api/cv/parse] ──> Returns Canonical CV JSON + Signed Source Ticket
        │
        ├───────────────────────────────────────┐
        ▼ (LLM #2: Fit Evaluator & Judge)        ▼ (LLM #3: CV Tailor & Enhancer)
[POST /api/cv/evaluate]                 [POST /api/cv/tailor]
(JOB_FIT or GENERAL_AUDIT report)        (Evidence-preserving bullet rewrites)
                                                │
                                                ▼ (Persistence & Entitlement Gate)
                                        [POST /api/cv/tailor-and-save]
                                        (Exportable CV Document & PDF Rendering)
```

1. **LLM #1 — CV Mapper / Structuring**:
   - Classifies and groups source atoms into canonical CV schema without authoring candidate text.
   - Guarantees 100% source provenance and rejects unmapped fallback documents on parse.
2. **LLM #2 — CV Evaluator & Judge**:
   - Computes overall fit score, category scores, skill match matrix, strengths, gaps, and actionable suggestions.
   - Operates in `JOB_FIT` mode with JD, or `GENERAL_AUDIT` mode without JD.
3. **LLM #3 — CV Tailor & Bullet Enhancer**:
   - Produces bounded, evidence-preserving rewrites on bullet points ($\le$ 2 operations, $\le$ 320 chars).
   - Hard server gates reject invented or removed numeric claims.
