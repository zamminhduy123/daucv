// ─── Re-export CVDocumentV2 types ────────────────────────────────────────────
import type {
  LayoutLine as _LayoutLine,
  CVDocumentV2 as _CVDocumentV2,
  CVTailoringDiagnostics as _CVTailoringDiagnostics,
} from "./cv-document-v2";

// Re-export for consumers
export type LayoutLine = _LayoutLine;
export { CURRENT_RECONSTRUCTION_VERSION } from "./cv-document-v2";

export interface FileInfo {
  id: string;
  user_id: string;
  bucket: string;
  object_path: string;
  original_filename: string;
  content_type: string;
  url: string;
  created_at?: string;
  updated_at?: string;
}

export interface RawExtractionReference {
  id: string;
  extraction_version: string;
  method: "native_blocks" | "word_layout" | "ocr";
}


export type {
  ContentOrigin,
  CVTextValue,
  CVSectionType,
  CVBlockMetadata,
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
  CVIdentitySourceMap,
  CVIdentity,
  CVUnmappedReason,
  LLMUnmappedReference,
  CVUnmappedContent,
  CVDocumentV2,
  CVRewriteDecision,
  CVTailoringDiagnostics,
  CVTranslationDecision,
  CVTranslationDiagnostics,
  CVTranslationVariant,
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
  layoutData: _LayoutLine[] | null;
  rawExtractionRef: RawExtractionReference | null;
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

export type CVDesign = "classic_ats" | "modern_professional" | "compact";

export interface CVTemplateDefinition {
  template_id: string;
  version: number;
  label: string;
  description: string;
  layout: "single_column" | "sidebar";
  ats_friendly: boolean;
  supports_multipage: boolean;
}

export interface CVRenderDiagnostics {
  render_version: number;
  document_hash: string;
  template_id: string;
  template_version: number;
  render_hash: string;
  page_count?: number | null;
  warnings: string[];
  missing_field_ids: string[];
  duplicate_field_ids: string[];
  mismatched_field_ids: string[];
  clipped_field_ids: string[];
  overlapping_field_ids: string[];
  is_valid: boolean;
}

export interface CVPreviewResponse {
  html: string;
  diagnostics: CVRenderDiagnostics;
  render_hash: string;
}

export interface TailoredCVVersion {
  id: string;
  target_role?: string | null;
  company_name?: string | null;
  jd_text: string;
  tailored_cv: TailoredCV;
  source_language?: "vi" | "en";
  // V2 typed document (nullable for legacy records)
  document_v2?: _CVDocumentV2 | null;
  source_document_v2?: _CVDocumentV2 | null;
  tailoring_diagnostics?: _CVTailoringDiagnostics | null;
  source_pdf_reference?: string | null;
  selected_design: CVDesign;
  template_id?: string | null;
  template_version?: number | null;
  render_version?: number | null;
  last_render_diagnostics?: CVRenderDiagnostics | null;
  document_schema_version?: number;
  reconstruction_version?: number;
  tailoring_pipeline_version?: number;
  reconstruction_status?: "current" | "outdated";
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
  source_language?: "vi" | "en";
  role_fit_score?: number;           // Raw LLM assessment — what a human recruiter gives
  match_score?: number;              // "CV Match" — penalized by missing JD keywords
  score_breakdown?: ScoreBreakdown;
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
  source_document_v2?: _CVDocumentV2 | null;
  reconstruction_diagnostics?: {
    reconstruction_version: number;
    warnings: string[];
    block_confidence: Record<string, number>;
  } | null;
  target_role?: string | null;
  company_name?: string | null;
  tailoring_entitlement: string;
  tailoring_diagnostics?: _CVTailoringDiagnostics | null;
}

export interface CVAnalysisEnvelope {
  analysis: Omit<CVAnalysisResponse, "tailored_cv" | "document_v2" | "source_document_v2" | "reconstruction_diagnostics" | "tailoring_entitlement">;
  tailored_cv: _CVDocumentV2;
  source_document_v2: _CVDocumentV2;
  reconstruction_diagnostics: NonNullable<CVAnalysisResponse["reconstruction_diagnostics"]>;
  legacy_tailored_cv: TailoredCV;
  tailoring_entitlement: string;
  tailoring_diagnostics: _CVTailoringDiagnostics | null;
}

// ─── Decoupled CV pipeline ─────────────────────────────────────────────────

export type CanonicalCV = Record<string, unknown>;

export type EvaluationMode = "GENERAL_AUDIT" | "JOB_FIT";
export type EvaluationGrade =
  | "EXCELLENT"
  | "STRONG_FIT"
  | "MODERATE_FIT"
  | "WEAK_FIT"
  | "NEEDS_IMPROVEMENT";

export interface CVEvaluationCategoryScores {
  technical_skills: number;
  experience_level: number;
  domain_fit: number;
  education_fit: number;
}

export interface CVSkillRequirementMatch {
  requirement: string;
  status: "matched" | "partial" | "missing";
  cv_evidence?: string | null;
  gap_explanation?: string | null;
}

export interface CVEvaluationReport {
  evaluation_mode: EvaluationMode;
  overall_fit_score: number;
  match_grade: EvaluationGrade | null;
  executive_summary: string | null;
  category_scores: CVEvaluationCategoryScores;
  key_strengths: string[];
  critical_gaps: string[];
  skill_matrix: CVSkillRequirementMatch[];
  actionable_recommendations: string[];
}

export interface CVTailoringChangeItem {
  path: string;
  original_text: string;
  proposed_text: string;
  rationale: string;
}

export interface CVTailoringResponse {
  tailored_cv: CanonicalCV;
  change_log: CVTailoringChangeItem[];
  tailoring_summary: string;
}

export interface CVPipelineAnalysis {
  canonical_cv: CanonicalCV;
  source_document_v2: _CVDocumentV2;
  source_ticket: string;
  evaluation: CVEvaluationReport;
  tailoring?: CVTailoringResponse;
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
