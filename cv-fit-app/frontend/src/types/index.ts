// ─── Workspace flow ───────────────────────────────────────────────────────────

export type WorkspaceStep = 1 | 2;

export interface WorkspaceInputs {
  jdText: string;
  cvText: string;
  cvFile: File | null;
}

// ─── AI Analysis Result ───────────────────────────────────────────────────────

export interface CVExperience {
  company: string;
  role: string;
  bullet_points: string[];
}

export interface TailoredCV {
  name: string;
  summary: string;
  experience: CVExperience[];
  skills: string[];
  education: string;
}

export interface MatchResult {
  match_score: number;
  missing_skills: string[];
  tailored_cv: TailoredCV;
}

export interface SuggestedEdit {
  section: string;
  original_text: string;
  upgraded_text: string;
  reason: string;
}

export interface CVAnalysisResponse {
  match_score: number;
  impact_score: number;
  tone: string;
  missing_keywords: string[];
  suggested_edits: SuggestedEdit[];
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
