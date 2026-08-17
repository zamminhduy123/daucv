// ─── CVDocumentV2 — Typed CV document model ──────────────────────────────────
//
// Replaces the legacy string-array sections (TailoredCV.sections: {title, items[]})
// with a discriminated-union block model that preserves semantic meaning:
//   entry blocks     — job / project records with title, subtitle, bullets
//   bullet blocks    — loose bullet points inside a section
//   paragraph blocks — plain text (summary, descriptions)
//   skill_group blocks — labeled skill categories
//   publication blocks — academic citations with authors, title, venue, date
//   education blocks — degree / institution / date records
//   unknown blocks   — content the parser could not confidently classify
//
// Every block carries stable source provenance so that parsing, rewriting, and
// validation can track which content survived, changed, or was rejected.

export type ContentOrigin = "extracted" | "llm_rewrite" | "user_edit";

export interface CVTextValue {
  value: string;
  source_block_ids: string[];
  origin: ContentOrigin;
}

// ─── Layout extraction metadata (Phase 3 — PDF → layout_data) ────────────────

export interface LayoutLine {
  text: string;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  font_size?: number | null;
  font_weight?: number | null;
  bullet_marker?: string | null;
  normalized_text: string;
  column_id?: string | null;
  joined_to_prev: boolean;
  is_page_break_marker: boolean;
  is_layout_artifact: boolean;
  page_height?: number | null;
  source_line_id?: string | null;
}

// ─── CVSectionType ────────────────────────────────────────────────────────────

export type CVSectionType =
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
  | "interests"
  | "custom";

// ─── Typed blocks (discriminated union via `type` tag) ───────────────────────

export interface CVBlockMetadata {
  confidence?: number;
  source_block_ids?: string[];
  source_line_ids?: string[];
  origin?: ContentOrigin;
  reconstruction_warnings?: string[];
  original_values?: Record<string, string | string[]>;
  tailored_values?: Record<string, string | string[]>;
}

export interface CVEntryBlock extends CVBlockMetadata {
  type: "entry";
  block_id: string;
  title: string;
  subtitle?: string;
  organization?: string;
  location?: string;
  date?: string;
  bullets: string[];
}

export interface CVBulletBlock extends CVBlockMetadata {
  type: "bullet";
  block_id: string;
  text: string;
}

export interface CVParagraphBlock extends CVBlockMetadata {
  type: "paragraph";
  block_id: string;
  text: string;
}

export interface CVSkillGroupBlock extends CVBlockMetadata {
  type: "skill_group";
  block_id: string;
  label?: string;
  skills: string[];
}

export interface CVPublicationBlock extends CVBlockMetadata {
  type: "publication";
  block_id: string;
  title: string;
  authors?: string;
  venue?: string;
  date?: string;
  status?: string;
}

export interface CVEducationBlock extends CVBlockMetadata {
  type: "education";
  block_id: string;
  institution?: string;
  degree?: string;
  field?: string;
  location?: string;
  date?: string;
  details: string[];
}

export interface CVUnknownBlock extends CVBlockMetadata {
  type: "unknown";
  block_id: string;
  lines: string[];
  confidence: number; // 0.0 – 1.0
}

export type CVBlockType =
  | CVEntryBlock
  | CVBulletBlock
  | CVParagraphBlock
  | CVSkillGroupBlock
  | CVPublicationBlock
  | CVEducationBlock
  | CVUnknownBlock;

// Backward-compatible alias
export type CVBlock = CVBlockType;

// ─── Section ─────────────────────────────────────────────────────────────────

export interface CVSection {
  id: string;
  type: CVSectionType;
  title: string;
  confidence: number;
  source_block_ids: string[];
  blocks: CVBlock[];
}

// ─── Identity ────────────────────────────────────────────────────────────────

export interface CVIdentitySourceMap {
  full_name: string[];
  headline: string[];
  email: string[];
  phone: string[];
  location: string[];
  links: Record<string, string[]>;
}

export interface CVIdentity {
  full_name: string | null;
  headline: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  links: string[];
  source_block_ids: string[];
  field_source_block_ids: CVIdentitySourceMap;

  /** @deprecated New consumers must use full_name. */
  name: string;
  /** @deprecated New consumers must use the structured contact fields. */
  contact_lines: string[];
}

// ─── Unmapped source content ────────────────────────────────────────────────

export type CVUnmappedReason =
  | "unknown_section"
  | "decorative_content"
  | "placeholder_content"
  | "ambiguous_content"
  | "parser_omission";

export interface LLMUnmappedReference {
  block_id: string;
  reason: Exclude<CVUnmappedReason, "parser_omission">;
  confidence: number | null;
}

export interface CVUnmappedContent {
  block_id: string;
  text: string;
  page: number;
  reason: CVUnmappedReason;
  confidence: number | null;
  fragment_id?: string;
  source_start?: number | null;
  source_end?: number | null;
}

// ─── Source Coverage Diagnostics (Phase 4) ──────────────────────────────────

export type CVSourceCoverageIssueCode =
  | "unknown_source_reference"
  | "substantive_source_omission"
  | "duplicate_semantic_ownership"
  | "ambiguous_source_match"
  | "unmatched_semantic_leaf"
  | "invalid_unmapped_reference";

export interface CVSourceCoverageIssue {
  code: CVSourceCoverageIssueCode;
  block_id: string;
  field_paths?: string[];
  significant_character_count?: number;
}

export interface CVSourceCoverageDiagnostics {
  raw_block_count: number;
  accounted_block_count: number;
  significant_character_count: number;
  mapped_character_count: number;
  benign_unmapped_character_count: number;
  substantive_unmapped_character_count: number;
  duplicate_character_count: number;
  coverage_ratio: number;
  issues: CVSourceCoverageIssue[];
}

export interface CVReconstructionDiagnostics {
  reconstruction_version: number;
  warnings: string[];
  block_confidence: Record<string, number>;
  source_coverage?: CVSourceCoverageDiagnostics | null;
}

// ─── Tailoring Rewrite Diagnostics (Phase 5) ────────────────────────────────

export interface CVRewriteDecision {
  operation_id: string;
  block_id: string;
  field: "text" | "bullets" | "skills";
  status: "accepted" | "rejected" | "preserved";
  reason_codes: string[];
  original_value_hash: string;
  proposed_value_hash: string;
}

export interface CVTailoringDiagnostics {
  rewrite_version: number;
  source_document_hash: string;
  jd_hash: string;
  accepted_count: number;
  rejected_count: number;
  preserved_count: number;
  used_fallback: boolean;
  decisions: CVRewriteDecision[];
}

// ─── Translation Variant Diagnostics (Phase 7) ─────────────────────────────

export interface CVTranslationDecision {
  field_id: string;
  status: "translated" | "preserved" | "rejected";
  reason_codes: string[];
  source_value_hash: string;
  translated_value_hash: string;
}

export interface CVTranslationDiagnostics {
  translation_version: number;
  source_document_hash: string;
  translated_document_hash: string;
  source_language: string;
  target_language: "vi" | "en";
  translated_count: number;
  preserved_count: number;
  rejected_count: number;
  decisions: CVTranslationDecision[];
  is_valid: boolean;
}

export interface CVTranslationVariant {
  id: string;
  user_id: string;
  tailored_cv_version_id: string;
  source_document_hash: string;
  translated_document_hash: string;
  source_language: string;
  target_language: "vi" | "en";
  translation_version: number;
  translator_version: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  operation_id: string;
  translated_document: CVDocumentV2;
  diagnostics: CVTranslationDiagnostics;
  created_at?: string;
  updated_at?: string;
}

// ─── Document V2 ─────────────────────────────────────────────────────────────

export const CURRENT_RECONSTRUCTION_VERSION = 4;

export interface CVDocumentV2 {
  raw_extraction_id: string | null;
  schema_version: 2;
  extraction_version: string;
  parser_version: string;
  reconstruction_version: number;
  requires_reprocessing: boolean;
  source_hash: string | null;
  identity: CVIdentity;
  summary: CVParagraphBlock | null;
  sections: CVSection[];
  unmapped_content: CVUnmappedContent[];
  reconstruction_warnings: string[];
  reconstruction_diagnostics?: CVReconstructionDiagnostics;
}
