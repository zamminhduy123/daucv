// ─── Re-export CVDocumentV2 types ────────────────────────────────────────────
import type { CVDocumentV2 as _CVDocumentV2 } from "./cv-document-v2";

export type {
  CVSectionType,
  CVBlockType,
  CVBlock,
  CVEntryBlock,
  CVBulletBlock,
  CVParagraphBlock,
  CVSkillGroupBlock,
  CVPublicationBlock,
  CVEducationBlock,
  CVUnknownBlock,
  CVSection,
  CVIdentity,
  CVDocumentV2,
} from "./cv-document-v2";

// ─── Workspace flow ───────────────────────────────────────────────────────────
// Types in this file are exported at module load time, so re-exported types
// from "./cv-document-v2" are available for use in interfaces below.

export type WorkspaceStep = 1 | 2;

export interface WorkspaceInputs {
  jdText: string;
  cvText: string;
  cvFile: File | null;
  jdFile: File | null;
}

// ─── AI Analysis Result ───────────────────────────────────────────────────────

export interface CVExperience {
  company: string;
  role: string;
  bullet_points: string[];
}

export interface TailoredCV {
  name: string;
  headline?: string;
  contact_lines?: string[];
  summary: string;
  sections?: TailoredCVSection[];
  experience: CVExperience[];
  skills: string[];
  education: string;
}

export interface TailoredCVSection {
  title: string;
  items: string[];
}

export type CVDesign = "classic_ats" | "modern_professional" | "compact_one_page";

export interface TailoredCVVersion {
  id: string;
  target_role?: string | null;
  company_name?: string | null;
  jd_text: string;
  tailored_cv: TailoredCV;
  // V2 typed document (nullable for legacy records)
  document_v2?: _CVDocumentV2 | null;
  selected_design: CVDesign;
  // Schema versioning metadata
  document_schema_version?: number;
  reconstruction_version?: number;
  source_hash?: string | null;
  jd_hash?: string | null;
  reconstruction_warnings?: string[];
  created_at: string;
  updated_at: string;
}

export interface MatchResult {
  match_score: number;
  missing_skills: string[];
  tailored_cv: TailoredCV;
}

export interface SuggestedEdit {
  section: string;
  original_text: string;
  improved_safe: string;
  improved_with_placeholders: string;
  metric_questions: string[];
  unsupported_assumptions: string[];
  rewrite_risk: "safe" | "needs_user_input" | "risky";
  reason: string;
  upgraded_text?: string;
}

export interface ScoreBreakdown {
  weights: Record<string, number>;
  raw_score: number;
  critical_missing_count: number;
  high_missing_count: number;
  weighted_missing_requirement_score: number;
  unsupported_claim_count: number;
  critical_missing_penalty: number;
  high_missing_penalty: number;
  missing_requirement_penalty: number;
  unsupported_claim_penalty: number;
  total_penalty: number;
  final_score: number;
}

export interface CVAnalysisResponse {
  source_language: "vi" | "en";
  role_fit_score: number;           // Raw LLM assessment — what a human recruiter gives
  match_score: number;              // "CV Match" — penalized by missing JD keywords
  score_breakdown: ScoreBreakdown;
  match_headline: string;
  match_summary: string;

  // 6 sub-scores (0-100)
  technical_match: number;
  experience_relevance: number;
  keyword_coverage: number;
  impact_evidence: number;
  tone_quality: number;
  ats_readiness: number;

  missing_keywords: string[];
  suggested_edits: SuggestedEdit[];

  // New widgets data
  cv_strengths: string[];
  prioritized_keywords: PrioritizedKeyword[];
  evidence_analysis: EvidenceAnalysis[];
  tailored_cv: TailoredCV;
  document_v2?: _CVDocumentV2 | null;
  target_role?: string | null;
  company_name?: string | null;
  tailoring_entitlement: string;
}

export interface PrioritizedKeyword {
  keyword: string;
  priority: "Critical" | "High" | "Medium" | "Low";
}

export interface EvidenceAnalysis {
  claim: string;
  evidence_strength: "Strong" | "Medium" | "Weak" | "Missing";
  comment: string;
}

// ─── Dashboard metric card ────────────────────────────────────────────────────

export interface MetricCardProps {
  label: string;
  value: string;
  sub: string;
  valueColor?: string;
  accentBg: string;
  icon: React.ReactNode;
}

// ─── Diff row ─────────────────────────────────────────────────────────────────

export interface DiffEntry {
  original: string;
  upgraded: string; // may contain safe HTML bold tags
}

// ─── Landing feature card ─────────────────────────────────────────────────────

export interface FeatureItem {
  icon: React.ElementType;
  title: string;
  body: string;
}

// ─── How it works step ────────────────────────────────────────────────────────

export interface HowItWorksStep {
  n: string;
  t: string;
  d: string;
}

// ─── Skill badge (landing mockup) ─────────────────────────────────────────────

export interface SkillBadge {
  skill: string;
  on: boolean;
}
