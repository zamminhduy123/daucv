# Tailored CV Structural Integrity — Stage-by-Stage Trace Summary

## Executive Summary

A full diagnostic trace was executed on the candidate source CV (`CV_DUYNGUYEN_2pu.pdf`) across all pipeline stages: layout extraction, text normalization, section boundary detection, V2 document reconstruction, and rendering parity.

Every observed output defect has been mapped to its exact first-divergence stage below.

---

## Pipeline Stage Audit Results

### Stage 1: Physical Extraction & Space Insertion
- **Total Pages**: 2 (Letter format)
- **Extracted Raw Characters**: 8,924
- **Extracted Logical Lines**: 142
- **First-Divergence Defect**: Missing spaces between words in specific PDF font/glyph spans:
  - `Achievedstate-of-the-artmulti-classclassificationresultsonthepublic...`
  - `Builtamultimodalvideoretrievalsystemforcompetition-scalesearchacross...`
- **Root Cause**: Bounding-box gap calculation in `layout_extraction.py` fails to insert spaces when glyph horizontal offsets are below a 2.0pt threshold in custom font matrices.

---

### Stage 2 & 3: Section Boundary Detection & Vocabulary Mapping
- **Total Detected Sections**: 4
  1. `Education` (type=`education`, 1 block)
  2. `Technical Skills` (type=`skills`, **47 blocks**)
  3. `Publications` (type=`publications`, 2 blocks)
  4. `Certifications` (type=`certifications`, 2 blocks)
- **First-Divergence Defect**: `Research Experience`, `Applied AI Projects`, and `Software Engineering Experience` were not recognized as valid section headings.
- **Root Cause**: Missing section header aliases in `SECTION_TITLE_MAP` in `section_detector.py`. As a result, all 47 lines under Research, Projects, and Work Experience were swallowed into the preceding `Technical Skills` section.

---

### Stage 4: Reconstructed Source Document (V2) & Record Boundaries
- **Reconstruction Warnings**:
  - `publication_parse_incomplete`
  - `possible_unjoined_line_wrap`
- **First-Divergence Defect**:
  - Employer records (Soonchunhyang University and Zalo - VNG Corporation) were flattened into unstructured `paragraph` blocks instead of structured `entry` blocks.
  - Education records for Soonchunhyang and HCM VNU were collapsed into a single education block.
  - Publication records duplicated raw citation content in title and metadata fields.
- **Root Cause**: Unrecognized section types (`skills`) fell back to generic `paragraph` block parsing without entry/bullet boundary splitting.

---

### Stage 5 & 6: Grounded Rewrite Safety & Hard Reconstruction Gate
- **Status**: Currently, low-confidence or structural fallback warnings (`publication_parse_incomplete`) log warnings but allow pipeline execution to proceed.
- **Remediation Requirement**: Implement a hard reconstruction gate that halts execution and preserves user credit if canonical section boundaries or record counts fail validation before LLM prompting.

---

## Defect to First-Divergence Stage Mapping

| Observed Defect | First-Divergence Stage | Source Module | Severity |
| :--- | :--- | :--- | :--- |
| Missing spaces in words (`Achievedstate...`) | **Stage 1** (Physical Extraction) | `layout_extraction.py` | High |
| Experience & Projects swallowed into `Technical Skills` | **Stage 3** (Section Vocabulary) | `section_detector.py` | Critical |
| Zalo & Research flattened into pipe/paragraph text | **Stage 4** (Block Reconstruction) | `cv_document_v2.py` | Critical |
| Education collapsed into 1 entry | **Stage 4** (Block Reconstruction) | `cv_document_v2.py` | High |
| Publication metadata content repetition | **Stage 4** (Publication Parsing) | `section_detector.py` | Medium |
| Unsupported claims (`MCP`, `LangGraph`) | **Stage 7** (Grounded Rewrite Gate) | `cv_quality_checks.py` | Critical |

---

## Audit Status: STAGE_TRACE_COMPLETED
Exit gate satisfied: Every visible PDF defect has been assigned a single named first-divergence stage.
