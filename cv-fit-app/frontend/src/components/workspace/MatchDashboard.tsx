"use client";

import type { CVAnalysisResponse, CVEvaluationReport, PrioritizedKeyword } from "@/types";
import { motion } from "framer-motion";
import {
  Code2,
  Briefcase,
  Tags,
  BarChart2,
  Pen,
  ShieldCheck,
  Sparkles,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  ClipboardCheck,
  Award,
  UserRound,
  ArrowUpRight,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";

const SUB_SCORES = [
  {
    key: "technical_match" as const,
    label: { vi: "Kỹ năng chuyên môn", en: "Technical skills" },
    icon: Code2,
    iconBg: "bg-green-50",
    iconColor: "text-green-600",
  },
  {
    key: "experience_relevance" as const,
    label: { vi: "Kinh nghiệm liên quan", en: "Relevant experience" },
    icon: Briefcase,
    iconBg: "bg-blue-50",
    iconColor: "text-blue-600",
  },
  {
    key: "keyword_coverage" as const,
    label: { vi: "Độ phủ từ khóa", en: "Keyword coverage" },
    icon: Tags,
    iconBg: "bg-yellow-50",
    iconColor: "text-yellow-600",
  },
  {
    key: "impact_evidence" as const,
    label: { vi: "Định lượng kết quả", en: "Impact evidence" },
    icon: BarChart2,
    iconBg: "bg-orange-50",
    iconColor: "text-orange-600",
  },
  {
    key: "tone_quality" as const,
    label: { vi: "Giọng văn", en: "Tone quality" },
    icon: Pen,
    iconBg: "bg-purple-50",
    iconColor: "text-purple-600",
  },
  {
    key: "ats_readiness" as const,
    label: { vi: "Điểm ATS", en: "ATS readiness" },
    icon: ShieldCheck,
    iconBg: "bg-teal-50",
    iconColor: "text-teal-600",
  },
] as const;

type AnalysisLanguage = "vi" | "en";

const ANALYSIS_COPY = {
  vi: {
    title: "Kết quả phân tích",
    generalSubtitle: "Đánh giá chất lượng CV của bạn",
    jdSubtitle: "Dựa trên JD và nội dung CV của bạn",
    overallAssessment: "Đánh giá chung",
    keywordAssessment: "Đánh giá từ khóa",
    penaltyTitle: "Vì sao điểm CV Match thấp hơn?",
    penaltyText: (roleFit: number, gap: number) => (
      <>Role Fit của bạn là <span className="font-bold">{roleFit}%</span>, nhưng điểm cuối bị trừ{" "}<span className="font-bold">{gap}</span> điểm vì CV còn thiếu hoặc chưa xác nhận một số tín hiệu ưu tiên trong JD.</>
    ),
    strengths: "Điểm sáng của CV",
    keywords: "Từ khóa cần bổ sung",
    keywordWarning: "Chỉ thêm những từ khóa này nếu bạn thực sự có kinh nghiệm liên quan.",
    evidence: "Phân tích Bằng chứng Năng lực",
    claim: "Năng lực / Claim",
    clarity: "Độ rõ ràng",
    comment: "Nhận xét",
  },
  en: {
    title: "Analysis Results",
    generalSubtitle: "An assessment of your CV quality",
    jdSubtitle: "Based on your CV and the job description",
    overallAssessment: "Overall assessment",
    keywordAssessment: "Keyword assessment",
    penaltyTitle: "Why is CV Match lower?",
    penaltyText: (roleFit: number, gap: number) => (
      <>Your Role Fit is <span className="font-bold">{roleFit}%</span>, but the final score is reduced by{" "}<span className="font-bold">{gap}</span> points because the CV is missing or has not confirmed some priority signals from the JD.</>
    ),
    strengths: "CV Strengths",
    keywords: "Keywords to Add",
    keywordWarning: "Add these keywords only if you genuinely have relevant experience.",
    evidence: "Capability Evidence Analysis",
    claim: "Capability / Claim",
    clarity: "Evidence strength",
    comment: "Comment",
  },
} as const;

const PRIORITY_LABELS: Record<AnalysisLanguage, Record<PrioritizedKeyword["priority"], string>> = {
  vi: { Critical: "Rất quan trọng", High: "Cao", Medium: "Trung bình", Low: "Thấp" },
  en: { Critical: "Critical", High: "High", Medium: "Medium", Low: "Low" },
};

const PRIORITY_BADGE_STYLE: Record<PrioritizedKeyword["priority"], string> = {
  Critical: "bg-red-100 text-red-700",
  High: "bg-orange-100 text-orange-700",
  Medium: "bg-yellow-100 text-yellow-700",
  Low: "bg-green-50 text-green-600",
};

// Compact circular progress gauge matching HTML mockup
function CompactCircularScore({
  score,
  label,
  color,
}: {
  score: number;
  label: string;
  color: string;
}) {
  const safeScore = typeof score === "number" && !isNaN(score) ? Math.round(score) : 0;
  const radius = 27;
  const circumference = 2 * Math.PI * radius; // ~169.64
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;

  return (
    <div className="text-center flex flex-col items-center">
      <div className="relative w-[64px] h-[64px]">
        <svg width="64" height="64" viewBox="0 0 64 64" className="-rotate-90">
          <circle
            cx="32"
            cy="32"
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="6"
          />
          <circle
            cx="32"
            cy="32"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: "stroke-dashoffset 1s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-medium text-gray-800">{safeScore}%</span>
        </div>
      </div>
      <p className="text-xs text-gray-500 mt-1 font-medium">{label}</p>
    </div>
  );
}

const PIPELINE_CARD_COPY = {
  technical_skills: {
    label: "Kỹ năng chuyên môn",
    description: "Nội dung chuyên môn phù hợp và thể hiện năng lực tốt.",
    icon: Code2,
    accent: "#12a873",
    iconBackground: "#e3f7ee",
    badgeBackground: "#e1f7ec",
  },
  experience_level: {
    label: "Kinh nghiệm",
    description: "Kinh nghiệm phù hợp và được trình bày rõ ràng.",
    icon: Briefcase,
    accent: "#1769e8",
    iconBackground: "#e7efff",
    badgeBackground: "#e5edff",
  },
  domain_fit: {
    label: "Phỏng vấn học",
    description: "Khả năng trả lời và tư duy giải quyết vấn đề rất tốt.",
    icon: Award,
    accent: "#d96b00",
    iconBackground: "#fff1e1",
    badgeBackground: "#fff1e2",
  },
  education_fit: {
    label: "Học vấn",
    description: "Nền tảng học vấn nổi bật và phù hợp với vị trí.",
    icon: UserRound,
    accent: "#7139dc",
    iconBackground: "#f0eaff",
    badgeBackground: "#f1eaff",
  },
} as const;

type PipelineScoreKey = keyof typeof PIPELINE_CARD_COPY;

function scoreStrength(score: number) {
  if (score >= 93) return "Excellent";
  if (score >= 91) return "Strong";
  if (score >= 75) return "Good";
  return "Needs work";
}

function displayGrade(grade: CVEvaluationReport["match_grade"], score: number) {
  if (grade) return grade.replaceAll("_", " ");
  if (score >= 90) return "EXCELLENT";
  if (score >= 75) return "STRONG";
  if (score >= 60) return "MODERATE";
  return "NEEDS IMPROVEMENT";
}

function LargeScoreRing({ score }: { score: number }) {
  const safeScore = Number.isFinite(score) ? Math.max(0, Math.min(100, Math.round(score))) : 0;
  const radius = 113;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (safeScore / 100) * circumference;

  return (
    <div className="relative mx-auto h-[180px] w-[180px]">
      <svg viewBox="0 0 280 280" className="h-full w-full -rotate-90" aria-label={`${safeScore} trên 100`}>
        <circle cx="140" cy="140" r={radius} fill="none" stroke="#edf0f4" strokeWidth="17" />
        <circle
          cx="140"
          cy="140"
          r={radius}
          fill="none"
          stroke="#12b67a"
          strokeWidth="17"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
      </svg>
      <Sparkles className="absolute right-[13px] top-[3px] h-7 w-7 text-[#66dcae]" strokeWidth={1.5} />
      <Sparkles className="absolute right-[0px] top-[0px] h-3 w-3 text-[#66dcae]" strokeWidth={1.5} />
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-1">
        <span className="text-[3rem] font-bold leading-none tracking-[-0.07em] text-[#101d38]">{safeScore}</span>
        <span className="mt-1 text-[1rem] font-semibold tracking-[-0.03em] text-[#64708a]">/100</span>
      </div>
    </div>
  );
}

function PipelineMetricCard({
  score,
  metric,
}: {
  score: number;
  metric: (typeof PIPELINE_CARD_COPY)[PipelineScoreKey];
}) {
  const safeScore = Number.isFinite(score) ? Math.round(score) : 0;
  const Icon = metric.icon;

  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col rounded-[15px] border border-[#e3e8ef] bg-white p-4 shadow-[0_2px_4px_rgba(20,42,75,0.015)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-full"
          style={{ backgroundColor: metric.iconBackground }}
        >
          <Icon className="h-6 w-6" style={{ color: metric.accent }} strokeWidth={2.1} />
        </div>
        <span
          className="rounded-md px-2.5 py-1 text-[0.68rem] font-semibold whitespace-nowrap"
          style={{ color: metric.accent, backgroundColor: metric.badgeBackground }}
        >
          Strength: {scoreStrength(safeScore)}
        </span>
      </div>

      <div className="mt-2">
        <p className="text-[1.65rem] font-bold leading-none tracking-[-0.05em] text-[#101d38]">{safeScore}%</p>
        <h3 className="mt-1 text-[0.86rem] font-semibold tracking-[-0.02em] text-[#101d38]">{metric.label}</h3>
      </div>

      <div className="mt-2.5 h-1 rounded-full bg-[#e5e9ef]">
        <div
          className="h-full rounded-full transition-[width] duration-1000 ease-out"
          style={{ width: `${Math.max(0, Math.min(100, safeScore))}%`, backgroundColor: metric.accent }}
        />
      </div>
      <p className="mt-2 max-w-[31rem] text-[0.72rem] leading-[1.35] text-[#71809a]">{metric.description}</p>
    </motion.article>
  );
}

function PipelineMatchDashboard({ report }: { report: CVEvaluationReport }) {
  const score = Number.isFinite(report.overall_fit_score) ? Math.round(report.overall_fit_score) : 0;
  const grade = displayGrade(report.match_grade, score);
  const overview = report.key_strengths[0] ?? "CV của bạn nổi bật ở nhiều tiêu chí quan trọng. Hãy tiếp tục phát huy thế mạnh và tinh chỉnh thêm các điểm nhỏ để hoàn thiện hơn nữa.";
  const metrics = (Object.keys(PIPELINE_CARD_COPY) as PipelineScoreKey[]).map((key) => ({
    key,
    metric: PIPELINE_CARD_COPY[key],
    score: report.category_scores[key],
  }));

  return (
    <div className="-m-1 min-h-full rounded-[22px] bg-[#f4f8ff] p-1 sm:-m-2 sm:p-2">
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-[1660px] rounded-[22px] border border-[#e8edf4] bg-white px-4 py-5 text-[#101d38] shadow-[0_10px_26px_rgba(63,94,143,0.08)] sm:px-6 lg:px-8 lg:py-5"
      >
        <header className="mb-4">
          <h1 className="text-[1.5rem] font-bold leading-tight tracking-[-0.04em] text-[#132957] sm:text-[1.75rem]">Overall Score</h1>
          <p className="mt-1 text-[0.76rem] leading-4 text-[#68758f] sm:text-[0.84rem]">
            {report.executive_summary ?? "General CV Audit: Candidate receives a complete quality assessment."}
          </p>
        </header>

        <div className="grid gap-4 lg:grid-cols-[minmax(290px,0.92fr)_minmax(0,1.58fr)] lg:gap-5">
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex  flex-col rounded-[16px] border border-[#e3e8ef] bg-white px-4 py-4 sm:px-5"
          >
            <div className="flex flex-col flex-1 items-center justify-center">
              <LargeScoreRing score={score} />
              <div className="mt-0 text-center">
                <p className="text-[1rem] font-bold uppercase tracking-[-0.03em] text-[#0eaa70]">{grade}</p>
                <p className="mt-0.5 text-[0.76rem] text-[#6d7992]">CV quality</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5 rounded-[11px] bg-[#effaf5] px-3 py-2.5 text-[#12213f]">
              <CheckCircle className="h-6 w-6 shrink-0 text-[#159b6e]" strokeWidth={1.8} />
              <p className="text-[0.72rem] leading-4">
                Your CV is strong and well-optimized.<br />
                Keep up the great work!
              </p>
            </div>
          </motion.div>

          <div className="grid gap-4 sm:grid-cols-2">
            {metrics.map(({ key, metric, score: metricScore }) => (
              <PipelineMetricCard key={key} metric={metric} score={metricScore} />
            ))}
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2.5 rounded-[12px] bg-[#f1f6ff] px-4 py-2.5 text-[#132957] sm:px-5">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#3d7fe8] text-white shadow-[0_3px_8px_rgba(61,127,232,0.2)]">
            <ArrowUpRight className="h-4 w-4" strokeWidth={2.2} />
          </span>
          <span className="text-[0.78rem] font-semibold">Tổng quan</span>
          <span className="hidden h-4 w-px bg-[#d4deef] sm:block" />
          <span className="text-[0.72rem] leading-4 text-[#62718d]">{overview}</span>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <CompactInsightPanel
            title="Điểm mạnh"
            items={report.key_strengths}
            icon={CheckCircle}
            accent="#159b6e"
            background="#effaf5"
          />
          <CompactInsightPanel
            title="Điểm yếu cần cải thiện"
            items={report.critical_gaps}
            icon={AlertTriangle}
            accent="#c97900"
            background="#fff7e9"
            emptyText="Chưa phát hiện khoảng trống nghiêm trọng trong phạm vi đánh giá."
          />
        </div>
      </motion.section>
    </div>
  );
}

function CompactInsightPanel({
  title,
  items,
  icon: Icon,
  accent,
  background,
  emptyText,
}: {
  title: string;
  items: string[];
  icon: typeof CheckCircle;
  accent: string;
  background: string;
  emptyText?: string;
}) {
  const visibleItems = items.length > 0 ? items.slice(0, 3) : [emptyText ?? "Chưa có dữ liệu."];

  return (
    <section className="rounded-[13px] border border-[#e7ebf1] bg-white px-4 py-3.5">
      <h2 className="flex items-center gap-2 text-[0.82rem] font-semibold text-[#132957]">
        <span className="flex h-6 w-6 items-center justify-center rounded-full" style={{ color: accent, backgroundColor: background }}>
          <Icon className="h-3.5 w-3.5" strokeWidth={2} />
        </span>
        {title}
      </h2>
      <ul className="mt-2.5 space-y-1.5">
        {visibleItems.map((item) => (
          <li key={item} className="flex items-start gap-2 text-[0.72rem] leading-4 text-[#6f7d95]">
            <span className="mt-[0.4rem] h-1 w-1 shrink-0 rounded-full" style={{ backgroundColor: accent }} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function MatchDashboard({ result }: { result: CVAnalysisResponse | CVEvaluationReport }) {
  if ("evaluation_mode" in result) {
    return <PipelineMatchDashboard report={result} />;
  }
  return <LegacyMatchDashboard result={result} />;
}

function LegacyMatchDashboard({ result }: { result: CVAnalysisResponse }) {
  const { jdText } = useWorkspace();
  const language = result.source_language ?? "vi";
  const copy = ANALYSIS_COPY[language];
  const isGeneral = !jdText?.trim();

  // Two scores: Role Fit (raw LLM) and CV Match (penalized)
  const rawRoleFit = result.role_fit_score ?? result.score_breakdown?.raw_score ?? result.match_score;
  const rawMatch = result.match_score ?? result.role_fit_score;

  const roleFitScore = typeof rawRoleFit === "number" && !isNaN(rawRoleFit) ? Math.round(rawRoleFit) : 0;
  const matchScore = typeof rawMatch === "number" && !isNaN(rawMatch) ? Math.round(rawMatch) : roleFitScore;
  const penaltyGap = roleFitScore - matchScore;
  const showPenaltyContext = !isGeneral && penaltyGap >= 8;

  // Penalty reason sublabel
  const penaltyReason = _getPenaltyReason(result, language);

  return (
    <div>
      {/* Page title */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8"
      >
        <h1
          style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 700, color: "#2F4F4F" }}
          className="mb-1"
        >
          {copy.title}
        </h1>
        <p className="text-lg text-[#2F4F4F]/70">
          {isGeneral ? copy.generalSubtitle : copy.jdSubtitle}
        </p>
      </motion.div>

      {/* Main Card — Structured after Sửa các lỗi sau.html */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white border border-gray-200/80 rounded-2xl p-6 shadow-sm mb-8"
      >
        {/* Card Header: Headline + Subtitle */}
        <h2 className="text-xl font-bold text-gray-900 mb-1">
          {result.match_headline || copy.title}
        </h2>
        <p className="text-xs text-gray-500 mb-5">
          {isGeneral ? copy.generalSubtitle : copy.jdSubtitle}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6 items-start">
          {/* Left Column (280px): Side-by-side Gauges + Explanation */}
          <div>
            <div className="flex items-center gap-5 mb-4">
              <CompactCircularScore
                score={roleFitScore}
                label="Role fit"
                color="#378ADD"
              />
              {!isGeneral && (
                <CompactCircularScore
                  score={matchScore}
                  label="CV match"
                  color={matchScore >= 70 ? "#059669" : matchScore >= 45 ? "#d97706" : "#D85A30"}
                />
              )}
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              {showPenaltyContext
                ? (language === "vi"
                  ? `Điểm giảm ${penaltyGap} điểm ${penaltyReason ? `do thiếu ${penaltyReason.replace(/^Bị trừ \d+ điểm vì còn thiếu /, "")}` : ""}. Xem chi tiết ở mục "Từ khóa cần bổ sung" bên dưới.`
                  : `Score reduced by ${penaltyGap} points ${penaltyReason ? `due to missing ${penaltyReason.replace(/^\d+-point deduction for /, "")}` : ""}. See "Keywords to Add" below for details.`)
                : result.match_summary}
            </p>
          </div>

          {/* Right Column (1fr): 3x2 Grid for 6 Sub-scores */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {SUB_SCORES.map(({ key, label, icon: Icon }, i) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.05 }}
                className="bg-gray-50/80 border border-gray-100 rounded-xl p-3.5 flex flex-col justify-between"
              >
                <Icon size={18} className="text-gray-500 mb-2" />
                <div>
                  <p className="text-2xl font-medium text-gray-900 leading-tight">
                    {result[key] ?? 0}%
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{label[language]}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* ── 2-Column Grid: Strengths & Prioritized Keywords ── */}
      {((result.cv_strengths?.length ?? 0) > 0 || (result.prioritized_keywords?.length ?? 0) > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Card A — CV Strengths */}
          {result.cv_strengths?.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-5">
                <div className="w-9 h-9 bg-green-50 rounded-xl flex items-center justify-center">
                  <Sparkles size={16} className="text-green-600" />
                </div>
                <h2 className="text-base font-bold text-[#2F4F4F]">{copy.strengths}</h2>
              </div>
              <div className="flex flex-col gap-3">
                {result.cv_strengths.map((s, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <CheckCircle size={15} className="text-green-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-700 leading-relaxed">{s}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Card B — Prioritized Keywords */}
          <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
              className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm flex flex-col"
            >
              <div className="flex items-center gap-3 mb-5">
                <div className="w-9 h-9 bg-orange-50 rounded-xl flex items-center justify-center">
                  <AlertTriangle size={16} className="text-orange-600" />
                </div>
                <h2 className="text-base font-bold text-[#2F4F4F]">{copy.keywords}</h2>
              </div>
              <div className="flex flex-wrap gap-2 mb-4 flex-1">
                {result.prioritized_keywords?.length > 0 ? result.prioritized_keywords.map(({ keyword, priority }, i) => {
                  const badgeStyle = PRIORITY_BADGE_STYLE[priority];
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-2 bg-gray-50 border border-gray-100 rounded-lg px-3 py-1.5"
                    >
                      <span className="text-sm text-gray-700 font-medium">{keyword}</span>
                      <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${badgeStyle}`}>
                        {PRIORITY_LABELS[language][priority]}
                      </span>
                    </div>
                  );
                }) : <span>Your CV matched all the prioritized keywords.</span>}
              </div>
              <div className="bg-yellow-50/50 border border-yellow-100 p-3 rounded-xl flex gap-2 mt-auto">
                <AlertTriangle size={14} className="text-yellow-600 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-yellow-800 leading-relaxed">
                  {copy.keywordWarning}
                </p>
              </div>
            </motion.div>
        </div>
      )}

      {/* ── Evidence Strength Table ── */}
      {result.evidence_analysis?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm mb-8 w-full overflow-x-auto"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="w-9 h-9 bg-blue-50 rounded-xl flex items-center justify-center">
              <ClipboardCheck size={16} className="text-blue-600" />
            </div>
            <h2 className="text-base font-bold text-[#2F4F4F]">{copy.evidence}</h2>
          </div>

          <table className="w-full text-left min-w-[500px]">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-4">
                  {copy.claim}
                </th>
                <th className="text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-4">
                  {copy.clarity}
                </th>
                <th className="text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3">
                  {copy.comment}
                </th>
              </tr>
            </thead>
            <tbody>
              {result.evidence_analysis.map(({ claim, evidence_strength, comment }, i) => {
                const strengthConfig = {
                  Strong: { color: "text-green-600", icon: CheckCircle, label: { vi: "Mạnh", en: "Strong" } },
                  Medium: { color: "text-orange-500", icon: HelpCircle, label: { vi: "Trung bình", en: "Medium" } },
                  Weak: { color: "text-red-500", icon: AlertTriangle, label: { vi: "Yếu", en: "Weak" } },
                  Missing: { color: "text-red-600", icon: XCircle, label: { vi: "Thiếu", en: "Missing" } },
                }[evidence_strength] ?? { color: "text-gray-400", icon: HelpCircle, label: evidence_strength };

                const StrengthIcon = strengthConfig.icon;

                return (
                  <tr
                    key={i}
                    className="border-b border-gray-50 last:border-0"
                  >
                    <td className="py-3 pr-4 text-sm font-medium text-[#2F4F4F]">{claim}</td>
                    <td className="py-3 pr-4">
                      <span className={`flex items-center gap-1.5 text-sm font-semibold ${strengthConfig.color}`}>
                        <StrengthIcon size={14} />
                        {typeof strengthConfig.label === "string" ? strengthConfig.label : strengthConfig.label[language]}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-gray-500">{comment}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </motion.div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helper: summarize penalty reason for CV Match sublabel
// ---------------------------------------------------------------------------

function _getPenaltyReason(
  result: CVAnalysisResponse,
  language: AnalysisLanguage,
): string {
  const { score_breakdown } = result;
  if (!score_breakdown) {
    return "";
  }

  const criticalCount = score_breakdown.critical_missing_count ?? 0;
  const highCount = score_breakdown.high_missing_count ?? 0;
  const totalPenalty = score_breakdown.total_penalty ?? 0;

  const parts: string[] = [];
  if (criticalCount) {
    parts.push(language === "vi" ? `${criticalCount} yêu cầu Critical` : `${criticalCount} Critical requirement(s)`);
  }
  if (highCount) {
    parts.push(language === "vi" ? `${highCount} yêu cầu High-priority` : `${highCount} High-priority requirement(s)`);
  }

  if (parts.length === 0) {
    if (!totalPenalty) return "";
    return language === "vi"
      ? `Bị trừ ${totalPenalty} điểm`
      : `${totalPenalty}-point deduction`;
  }

  return language === "vi"
    ? `Bị trừ ${totalPenalty} điểm vì còn thiếu ${parts.join(", ")}`
    : `${totalPenalty}-point deduction for ${parts.join(", ")}`;
}
