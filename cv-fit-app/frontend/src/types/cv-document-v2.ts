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
// Every block carries a stable `block_id` so that LLM rewriting and validation
// can track which content survived, changed, or was rejected.

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
  source_line_ids?: string[];
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
  blocks: CVBlock[];
}

// ─── Identity ────────────────────────────────────────────────────────────────

export interface CVIdentity {
  name?: string;
  headline?: string;
  contact_lines?: string[];
}

// ─── Document V2 ─────────────────────────────────────────────────────────────

export interface CVDocumentV2 {
  schema_version: 2;
  reconstruction_version?: number;
  identity: CVIdentity;
  summary?: CVParagraphBlock;
  sections: CVSection[];
  reconstruction_warnings?: string[];
}
