"use client";

import type { CVAnalysisResponse } from "@/types";
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
} from "lucide-react";

const SUB_SCORES = [
  {
    key: "technical_match" as const,
    label: "Kỹ năng chuyên môn",
    icon: Code2,
    iconBg: "bg-green-50",
    iconColor: "text-green-600",
  },
  {
    key: "experience_relevance" as const,
    label: "Kinh nghiệm liên quan",
    icon: Briefcase,
    iconBg: "bg-blue-50",
    iconColor: "text-blue-600",
  },
  {
    key: "keyword_coverage" as const,
    label: "Độ phủ từ khóa",
    icon: Tags,
    iconBg: "bg-yellow-50",
    iconColor: "text-yellow-600",
  },
  {
    key: "impact_evidence" as const,
    label: "Định lượng kết quả",
    icon: BarChart2,
    iconBg: "bg-orange-50",
    iconColor: "text-orange-600",
  },
  {
    key: "tone_quality" as const,
    label: "Giọng văn (tone)",
    icon: Pen,
    iconBg: "bg-purple-50",
    iconColor: "text-purple-600",
  },
  {
    key: "ats_readiness" as const,
    label: "ATS score",
    icon: ShieldCheck,
    iconBg: "bg-teal-50",
    iconColor: "text-teal-600",
  },
] as const;

// SVG circular progress ring
function CircularScore({ score }: { score: number }) {
  const radius = 57;
  const circumference = 2 * Math.PI * radius;
  const strokeDash = (score / 100) * circumference;

  return (
    <div className="relative w-full aspect-square">
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
          stroke="var(--primary)"
          strokeLinecap="round"
          strokeDasharray={`${strokeDash} ${circumference}`}
          style={{ transition: "stroke-dasharray 1s ease" }}
        />
      </svg>
      {/* Center text — number + label stacked */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5">
        <div className="flex items-baseline gap-0.5">
          <span className="text-5xl font-semibold text-[#1F2E2E] leading-none">{score}</span>
          <span className="text-xl font-bold text-[#1F2E2E] leading-none">%</span>
        </div>
        <span className="text-xs font-semibold text-gray-400 tracking-wide mt-1">JD Match</span>
      </div>
    </div>
  );
}

export default function MatchDashboard({ result }: { result: CVAnalysisResponse }) {

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
          Kết quả phân tích
        </h1>
        <p className="text-lg text-[#2F4F4F]/70">Dựa trên JD và nội dung CV của bạn</p>
      </motion.div>

      {/* Main Card */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white border border-gray-100 rounded-[2rem] p-6 md:p-8 shadow-sm flex flex-col xl:flex-row gap-8 items-center w-full mb-8"
      >
        {/* LEFT — Circular score, fills the column */}
        <div className="xl:w-[20%] w-full max-w-[200px] mx-auto xl:mx-0 flex-shrink-0">
          <CircularScore score={result.match_score} />
        </div>

        {/* RIGHT — Headline spanning above summary + 6 cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 flex-1 text-left">
          {/* Summary + 6 cards side by side */}
          <div className="flex flex-col gap-2 items-start mt-4">
            {/* Headline spans full width */}
            <h2 className="text-xl lg:max-w-[90%] font-bold text-[#2F4F4F] leading-tight">
              {result.match_headline}
            </h2>
            {/* Summary text */}
            <p className="text-xs text-gray-500 leading-relaxed flex-shrink-0 text-justify lg:max-w-[80%]">
              {result.match_summary}
            </p>
          </div>
          {/* 6 mini-score cards */}
          <div className="grid grid-cols-2 lg:grid-cols-3 mt-4 lg:mt-0 gap-3 flex-1 w-full">
            {SUB_SCORES.map(({ key, label, icon: Icon, iconBg, iconColor }, i) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.05 }}
                className="bg-white border border-gray-100 rounded-2xl p-4 flex flex-col items-start gap-2 shadow-sm"
              >
                <div className="flex items-center gap-2 w-full">
                  <div className={`${iconBg} rounded-lg p-1.5 flex-shrink-0`}>
                    <Icon size={14} className={iconColor} />
                  </div>
                  <span className="text-xl font-bold text-[#2F4F4F] leading-none">
                    {result[key] ?? 0}%
                  </span>
                </div>
                <p className="text-xs text-gray-500 font-medium leading-tight">{label}</p>
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
                <h2 className="text-base font-bold text-[#2F4F4F]">Điểm sáng của CV</h2>
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
          {result.prioritized_keywords?.length > 0 && (
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
                <h2 className="text-base font-bold text-[#2F4F4F]">Từ khóa cần bổ sung</h2>
              </div>
              <div className="flex flex-wrap gap-2 mb-4 flex-1">
                {result.prioritized_keywords.map(({ keyword, priority }, i) => {
                  const badgeStyle =
                    priority === "High"
                      ? "bg-red-50 text-red-600"
                      : priority === "Medium"
                        ? "bg-orange-50 text-orange-600"
                        : "bg-green-50 text-green-600";
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-2 bg-gray-50 border border-gray-100 rounded-lg px-3 py-1.5"
                    >
                      <span className="text-sm text-gray-700 font-medium">{keyword}</span>
                      <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${badgeStyle}`}>
                        {priority}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="bg-yellow-50/50 border border-yellow-100 p-3 rounded-xl flex gap-2 mt-auto">
                <AlertTriangle size={14} className="text-yellow-600 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-yellow-800 leading-relaxed">
                  Chỉ thêm những từ khóa này nếu bạn thực sự có kinh nghiệm liên quan.
                </p>
              </div>
            </motion.div>
          )}
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
            <h2 className="text-base font-bold text-[#2F4F4F]">Phân tích Bằng chứng Năng lực</h2>
          </div>

          <table className="w-full text-left min-w-[500px]">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-4">
                  Năng lực / Claim
                </th>
                <th className="text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-4">
                  Độ rõ ràng
                </th>
                <th className="text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3">
                  Nhận xét
                </th>
              </tr>
            </thead>
            <tbody>
              {result.evidence_analysis.map(({ claim, evidence_strength, comment }, i) => {
                const strengthConfig = {
                  Strong: { color: "text-green-600", icon: CheckCircle, label: "Strong" },
                  Medium: { color: "text-orange-500", icon: HelpCircle, label: "Medium" },
                  Weak: { color: "text-red-500", icon: AlertTriangle, label: "Weak" },
                  Missing: { color: "text-red-600", icon: XCircle, label: "Missing" },
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
                        {strengthConfig.label}
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
