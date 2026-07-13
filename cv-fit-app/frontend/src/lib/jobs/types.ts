/** Shared job search types — frontend consumes these from the backend API response. */

export interface CandidateProfile {
  targetRoles: string[];
  seniority: "intern" | "fresher" | "junior" | "middle" | "senior" | "unknown";
  skills: string[];
  location?: string;
  summary?: string;
  yearsOfExperience?: number;
}

export interface JobResult {
  id: string;
  source: "itviec" | "topcv" | "vietnamworks" | "glints" | "ybox" | "jobsgo" | "careerviet" | "vieclam24h";
  title: string;
  company?: string;
  companyLogoUrl?: string | null;
  location?: string;
  salary?: string;
  level?: "intern" | "fresher" | "junior" | "middle" | "senior" | "unknown";
  skills: string[];
  postedText?: string;
  url: string;
  descriptionSnippet?: string;
}

export interface RankedJobResult extends JobResult {
  matchScore: number;
  matchLabel: "good_match" | "stretch";
  matchReasons: string[];
  missingSkills: string[];
}

export interface JobSourceStatus {
  source: string;
  status: "success" | "empty" | "failed" | "timeout";
  count: number;
  error?: string;
}
