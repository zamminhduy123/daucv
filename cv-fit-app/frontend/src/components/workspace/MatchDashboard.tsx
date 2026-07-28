"use client";

import type { CVAnalysisResponse, PrioritizedKeyword } from "@/types";
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
  UserCheck,
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

// SVG circular progress ring — color tracks score severity
function CircularScore({
  score,
  label,
  sublabel,
  icon: Icon,
  evaluationLabel,
}: {
  score: number;
  label: string;
  sublabel?: string;
  icon: React.ElementType;
  evaluationLabel: string;
}) {
  const safeScore = typeof score === "number" && !isNaN(score) ? Math.round(score) : 0;
  const radius = 57;
  const circumference = 2 * Math.PI * radius;
  const strokeDash = (safeScore / 100) * circumference;

  // Color tracks severity: green (good) → amber (ok) → red (bad)
  const strokeColor =
    safeScore >= 70 ? "#059669" : safeScore >= 45 ? "#d97706" : "#dc2626";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-[140px] h-[140px]">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          {/* Background ring */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            strokeWidth="5"
            fill="none"
            className="stroke-gray-100"
          />
          {/* Progress ring */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            strokeWidth="5"
            fill="none"
            stroke={strokeColor}
            strokeLinecap="round"
            strokeDasharray={`${strokeDash} ${circumference}`}
            style={{ transition: "stroke-dasharray 1s ease" }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-0">
          <div className="flex items-baseline gap-0.5">
            <span className="text-4xl font-semibold text-[#1F2E2E] leading-none">{safeScore}</span>
            <span className="text-lg font-bold text-[#1F2E2E] leading-none">%</span>
          </div>
          <span className="text-[10px] font-semibold text-gray-400 tracking-wide mt-0.5">
            {label}
          </span>
        </div>
      </div>
      {/* Sublabel below gauge */}
      {sublabel && (
        <p className="text-[10px] text-gray-500 text-center leading-tight max-w-[140px]">
          {sublabel}
        </p>
      )}
      {/* Bottom icon indicator */}
      <div className="flex items-center gap-1.5">
        <Icon size={14} className={safeScore >= 70 ? "text-green-600" : safeScore >= 45 ? "text-yellow-600" : "text-red-600"} />
        <span className="text-xs font-semibold text-gray-500">
          {evaluationLabel}
        </span>
      </div>
    </div>
  );
}

export default function MatchDashboard({ result }: { result: CVAnalysisResponse }) {
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

  // Penalty reason sublabel for CV Match gauge
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

      {/* Main Card */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white border border-gray-100 rounded-[2rem] p-6 md:p-8 shadow-sm flex flex-col xl:flex-row gap-8 w-full mb-8"
      >
        {/* LEFT — Gauges column */}
        <div className="flex xl:flex-col flex-row xl:items-center justify-center gap-8 xl:gap-6 flex-shrink-0">
          {/* Role Fit gauge */}
          <CircularScore
            score={roleFitScore}
            label="Role Fit"
            icon={UserCheck}
            evaluationLabel={copy.overallAssessment}
          />

          {/* CV Match gauge (only when JD provided) */}
          {!isGeneral && (
            <CircularScore
              score={matchScore}
              label="CV Match"
              sublabel={showPenaltyContext ? penaltyReason : undefined}
              icon={AlertTriangle}
              evaluationLabel={copy.keywordAssessment}
            />
          )}
        </div>

        {/* RIGHT — Headline + 6 sub-score cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 flex-1 text-justify">
          {/* Summary + penalty context */}
          <div className="flex flex-col gap-2 items-center">
            <h2 className="text-xl lg:max-w-[90%] font-bold text-[#2F4F4F] leading-tight">
              {result.match_headline}
            </h2>
            <p className="text-xs text-gray-500 leading-relaxed flex-shrink-0 text-justify lg:max-w-[90%]">
              {result.match_summary}
            </p>

            {/* Penalty explanation card */}
            {showPenaltyContext && (
              <div className="mt-3 w-full lg:max-w-[90%] rounded-2xl border border-orange-100 bg-orange-50/70 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wide text-orange-700">
                      {copy.penaltyTitle}
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-orange-800">
                      {copy.penaltyText(roleFitScore, penaltyGap)}
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <p className="text-[11px] text-orange-700">Role Fit</p>
                    <p className="text-xl font-bold text-orange-800">{roleFitScore}%</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 6 mini-score cards */}
          <div className="grid grid-cols-2 lg:grid-cols-3 mt-4 lg:mt-0 gap-3 flex-1 w-full">
            {SUB_SCORES.map(({ key, label, icon: Icon, iconBg, iconColor }, i) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.05 }}
                className="bg-white border border-gray-100 rounded-2xl p-4 flex flex-col items-center justify-center gap-2 shadow-sm"
              >
                <div className="flex items-center gap-2 w-full justify-center">
                  <div className={`${iconBg} rounded-lg p-1.5 flex-shrink-0`}>
                    <Icon size={14} className={iconColor} />
                  </div>
                  <span className="text-xl font-bold text-[#2F4F4F] leading-none">
                    {result[key] ?? 0}%
                  </span>
                </div>
                <p className="text-xs text-gray-500 text-center font-medium leading-tight">{label[language]}</p>
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
