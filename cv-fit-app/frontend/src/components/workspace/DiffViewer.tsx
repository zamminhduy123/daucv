import { Pen, ArrowRight, ArrowDown, HelpCircle, AlertTriangle, ShieldCheck } from "lucide-react";
import type { SuggestedEdit } from "@/types";
import { motion } from "framer-motion";

const RISK_CONFIG = {
  safe: {
    label: "Safe",
    className: "bg-green-100/80 text-green-700",
    icon: ShieldCheck,
  },
  needs_user_input: {
    label: "Needs input",
    className: "bg-yellow-100/80 text-yellow-700",
    icon: HelpCircle,
  },
  risky: {
    label: "Risky",
    className: "bg-red-100/80 text-red-700",
    icon: AlertTriangle,
  },
} as const;

function RichText({ html, className }: { html: string; className: string }) {
  return (
    <p
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export default function DiffViewer({ edits }: { edits: SuggestedEdit[] }) {
  if (!edits || edits.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="mb-8"
    >
      <div className="bg-white border border-gray-100 rounded-3xl p-6 md:p-8 shadow-sm">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 bg-purple-50 rounded-xl flex items-center justify-center">
            <Pen size={16} className="text-purple-500" />
          </div>
          <h2 className="text-base font-bold text-[#2F4F4F]">Suggested Rewrites</h2>
        </div>

        {/* Edit entries */}
        <div className="flex flex-col gap-5">
          {edits.map((entry, index) => {
            const riskConfig = RISK_CONFIG[entry.rewrite_risk] ?? RISK_CONFIG.needs_user_input;
            const RiskIcon = riskConfig.icon;

            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + index * 0.08 }}
                className="flex flex-col gap-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-bold text-[#2F4F4F]">{entry.section}</h3>
                  <span className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${riskConfig.className}`}>
                    <RiskIcon size={12} />
                    {riskConfig.label}
                  </span>
                </div>

                {/* Side-by-side cards */}
                <div className="flex flex-col md:flex-row md:items-stretch gap-2">
                  {/* Original card */}
                  <div className="flex-1 border border-gray-100 rounded-2xl p-5 bg-gray-50">
                    <span className="text-[11px] uppercase tracking-wider text-gray-700 mb-2.5 block font-bold">
                      Original
                    </span>
                    <p className="text-sm text-gray-500 leading-relaxed">
                      {entry.original_text}
                    </p>
                  </div>

                  {/* Arrow connector */}
                  <div className="flex items-center justify-center flex-shrink-0">
                    {/* Desktop horizontal arrow */}
                    <div className="hidden md:flex w-8 h-8 items-center justify-center">
                      <ArrowRight size={18} className="text-green-400" />
                    </div>
                    {/* Mobile vertical arrow */}
                    <div className="flex md:hidden w-8 h-8 items-center justify-center mx-auto">
                      <ArrowDown size={18} className="text-green-400" />
                    </div>
                  </div>

                  {/* Improved card */}
                  <div className="flex-1 bg-green-50/60 border border-green-100 rounded-2xl p-5">
                    <span className="inline-block text-[11px] font-semibold uppercase tracking-wider text-green-600 bg-green-100/80 px-2 py-0.5 rounded mb-2.5">
                      Safe final rewrite
                    </span>
                    <RichText
                      html={entry.improved_safe}
                      className="text-sm text-gray-800 font-semibold leading-relaxed [&>strong]:font-bold [&>strong]:text-[#2F4F4F]"
                    />
                    {/* Reason — inline under improved text */}
                    {entry.reason && (
                      <p className="mt-3 text-xs text-gray-400 leading-relaxed">
                        <span className="font-semibold text-gray-500">Why this is better:</span>{" "}
                        {entry.reason}
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <div className="bg-blue-50/60 border border-blue-100 rounded-2xl p-5">
                    <span className="inline-block text-[11px] font-semibold uppercase tracking-wider text-blue-600 bg-blue-100/80 px-2 py-0.5 rounded mb-2.5">
                      Metric coaching version
                    </span>
                    <RichText
                      html={entry.improved_with_placeholders}
                      className="text-sm text-gray-700 font-medium leading-relaxed [&>strong]:font-bold [&>strong]:text-[#2F4F4F]"
                    />
                  </div>

                  <div className="bg-white border border-gray-100 rounded-2xl p-5">
                    {entry.metric_questions?.length > 0 && (
                      <div>
                        <span className="text-[11px] uppercase tracking-wider text-gray-700 mb-2.5 block font-bold">
                          Questions to quantify
                        </span>
                        <ul className="flex flex-col gap-2">
                          {entry.metric_questions.map((question, questionIndex) => (
                            <li key={questionIndex} className="flex items-start gap-2 text-sm text-gray-600 leading-relaxed">
                              <HelpCircle size={14} className="text-blue-500 mt-0.5 flex-shrink-0" />
                              <span>{question}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {entry.unsupported_assumptions?.length > 0 && (
                      <div className={entry.metric_questions?.length > 0 ? "mt-4 pt-4 border-t border-gray-100" : ""}>
                        <span className="text-[11px] uppercase tracking-wider text-gray-700 mb-2.5 block font-bold">
                          Unsupported assumptions
                        </span>
                        <ul className="flex flex-col gap-2">
                          {entry.unsupported_assumptions.map((assumption, assumptionIndex) => (
                            <li key={assumptionIndex} className="flex items-start gap-2 text-sm text-gray-600 leading-relaxed">
                              <AlertTriangle size={14} className="text-orange-500 mt-0.5 flex-shrink-0" />
                              <span>{assumption}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
