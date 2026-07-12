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

export interface CVEntryBlock {
  type: "entry";
  block_id: string;
  title: string;
  subtitle?: string;
  organization?: string;
  location?: string;
  date?: string;
  bullets: string[];
}

export interface CVBulletBlock {
  type: "bullet";
  block_id: string;
  text: string;
}

export interface CVParagraphBlock {
  type: "paragraph";
  block_id: string;
  text: string;
}

export interface CVSkillGroupBlock {
  type: "skill_group";
  block_id: string;
  label?: string;
  skills: string[];
}

export interface CVPublicationBlock {
  type: "publication";
  block_id: string;
  title: string;
  authors?: string;
  venue?: string;
  date?: string;
  status?: string;
}

export interface CVEducationBlock {
  type: "education";
  block_id: string;
  institution?: string;
  degree?: string;
  field?: string;
  location?: string;
  date?: string;
  details: string[];
}

export interface CVUnknownBlock {
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
  identity: CVIdentity;
  summary?: CVParagraphBlock;
  sections: CVSection[];
}
