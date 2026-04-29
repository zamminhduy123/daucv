"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import {
  Sparkles,
  CheckCircle,
  Copy,
  TrendingUp,
  Zap,
  Target,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";
import { useState } from "react";
import type { TemplateData } from "@/components/landing/TemplateView";

const IconMap: Record<string, React.ElementType> = {
  Target,
  Zap,
  TrendingUp,
  Sparkles,
};

/**
 * A variant of TemplateView designed to live inside the /app dashboard layout.
 * - No LandingNavbar / Footer (handled by AppLayout)
 * - Back button links to /app/templates
 * - CTA links to /app/analyzer
 */
export default function TemplateViewApp({ data }: { data: TemplateData }) {
  const [copied, setCopied] = useState(false);

  const generateCVText = () => {
    const { template } = data;
    return `${template?.name || ""}
${template?.title || ""}
${template.contact}

SUMMARY
${template.summary}

SKILLS
${template.skills.join("\n")}

EXPERIENCE
${template.experience
  .map(
    (exp) => `
${exp.role} | ${exp.company} | ${exp.period}
${exp.achievements.map((a) => `• ${a}`).join("\n")}
`
  )
  .join("\n")}

EDUCATION
${template.education}`;
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(generateCVText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Back link */}
      <Link
        href="/app/templates"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-[var(--primary)] transition-colors no-underline mb-6"
      >
        <ArrowLeft size={15} />
        Thư viện Mẫu CV
      </Link>

      {/* Hero area */}
      <div className="grid lg:grid-cols-2 gap-10 items-center mb-12">
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[var(--primary)]/10 rounded-full border border-[var(--primary)]/20 mb-5">
            <Sparkles className="w-3.5 h-3.5 text-[var(--primary)]" />
            <span className="text-xs font-semibold text-[#2F4F4F]">Mẫu CV được tin dùng bởi 1000+ ứng viên</span>
          </div>
          <h1
            className="font-heading font-bold text-[#2F4F4F] mb-4 leading-tight"
            style={{ fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)" }}
          >
            {data.title}
          </h1>
          <p className="text-[#5A6D6D] leading-relaxed mb-6 text-sm lg:text-base">{data.subtitle}</p>
          <div className="flex flex-wrap gap-3">
            <Link href="/app/analyzer">
              <button className="group px-6 py-3 bg-[var(--primary)] text-white rounded-xl font-semibold hover:opacity-90 transition-all shadow-md flex items-center gap-2 text-sm">
                Tùy chỉnh với AI
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </Link>
            <button
              onClick={handleCopy}
              className="px-6 py-3 bg-white text-[#2F4F4F] rounded-xl font-semibold transition-all border border-gray-200 hover:border-[var(--primary)]/40 flex items-center gap-2 text-sm"
            >
              {copied ? (
                <>
                  <CheckCircle className="w-4 h-4 text-[var(--primary)]" />
                  Đã copy!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy text mẫu
                </>
              )}
            </button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="hidden lg:flex justify-center"
        >
          <div className="relative bg-white p-8 rounded-3xl border-2 border-[var(--primary)]/20 shadow-xl flex flex-col items-center justify-center h-52 w-52">
            <Image src="/main-icon.webp" alt="Bé Đậu CV Expert" width={80} height={80} className="mb-3 drop-shadow-md" />
            <p className="font-semibold text-[#2F4F4F] text-sm">Bé Đậu - CV Expert</p>
            <p className="text-xs text-[#5A6D6D]">Chuyên gia tối ưu CV</p>
          </div>
        </motion.div>
      </div>

      {/* Content: Pro Tips + Template Preview */}
      <div className="grid lg:grid-cols-5 gap-8 mb-10">
        {/* Pro Tips */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="lg:col-span-2 space-y-4"
        >
          <h2 className="font-heading font-bold text-[#2F4F4F] text-xl mb-4">Bí quyết Đậu chia sẻ</h2>
          {data.proTips.map((tip, i) => {
            const IconComp = IconMap[tip.icon] || Sparkles;
            return (
              <div
                key={i}
                className="group bg-white p-5 rounded-2xl border border-[var(--primary)]/10 hover:border-[var(--primary)]/30 hover:shadow-sm transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 bg-[var(--primary)]/10 rounded-xl flex items-center justify-center flex-shrink-0">
                    <IconComp className="w-4 h-4 text-[var(--primary)]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#2F4F4F] text-sm mb-1">{tip.title}</h3>
                    <p className="text-xs text-[#5A6D6D] leading-relaxed">{tip.description}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </motion.div>

        {/* Template Preview */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="lg:col-span-3"
        >
          <div className="bg-white rounded-3xl shadow-lg border border-[var(--primary)]/10 overflow-hidden">
            {/* Header bar */}
            <div className="bg-[var(--primary)]/5 px-6 py-4 border-b border-[var(--primary)]/10 flex items-center justify-between">
              <div>
                <p className="font-semibold text-[#2F4F4F] text-sm">Template Preview</p>
                <p className="text-xs text-[#5A6D6D]">Mẫu CV chuẩn ATS cho {data.name}</p>
              </div>
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 bg-white text-[#2F4F4F] rounded-lg text-xs font-medium border border-[var(--primary)]/20 hover:border-[var(--primary)]/40 flex items-center gap-1.5 transition-colors"
              >
                <Copy className="w-3.5 h-3.5" />
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>

            {/* CV content */}
            <div className="p-8 text-left" style={{ fontFamily: "Arial, sans-serif" }}>
              <div className="text-center border-b-2 border-[#2F4F4F]/10 pb-5 mb-5">
                <h1 className="text-2xl font-bold text-[#2F4F4F] mb-1">{data.template.name}</h1>
                <p className="text-base text-[var(--primary)] font-semibold mb-2">{data.template.title}</p>
                <p className="text-xs text-[#5A6D6D]">{data.template.contact}</p>
              </div>

              {[
                { label: "Summary", content: <p className="text-xs text-[#2F4F4F] leading-relaxed">{data.template.summary}</p> },
                {
                  label: "Skills",
                  content: (
                    <div className="space-y-1">
                      {data.template.skills.map((s, i) => (
                        <p key={i} className="text-xs text-[#2F4F4F]">• {s}</p>
                      ))}
                    </div>
                  ),
                },
                {
                  label: "Experience",
                  content: (
                    <div className="space-y-4">
                      {data.template.experience.map((exp, i) => (
                        <div key={i}>
                          <div className="flex justify-between items-start mb-1">
                            <div>
                              <p className="font-bold text-xs text-[#2F4F4F]">{exp.role}</p>
                              <p className="text-xs text-[#5A6D6D]">{exp.company}</p>
                            </div>
                            <p className="text-xs text-[#5A6D6D] italic">{exp.period}</p>
                          </div>
                          <ul className="space-y-0.5">
                            {exp.achievements.map((a, j) => (
                              <li key={j} className="text-xs text-[#2F4F4F] leading-relaxed">• {a}</li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  ),
                },
                { label: "Education", content: <p className="text-xs text-[#2F4F4F]">{data.template.education}</p> },
              ].map(({ label, content }) => (
                <div key={label} className="mb-5">
                  <h2 className="text-xs font-bold text-[#2F4F4F] mb-2 uppercase tracking-wider border-l-4 border-[var(--primary)] pl-2">
                    {label}
                  </h2>
                  {content}
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Bottom CTA strip */}
      <div className="bg-[var(--primary)] rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <p className="font-bold text-white text-base mb-1">Đừng copy máy móc. Hãy để AI làm việc cho bạn.</p>
          <p className="text-white/80 text-sm">Bé Đậu sẽ tinh chỉnh mẫu CV này khớp với Job Description của bạn trong 5 giây.</p>
        </div>
        <Link href="/app/analyzer" className="flex-shrink-0">
          <button className="group px-6 py-3 bg-white text-[var(--primary)] rounded-xl font-bold hover:scale-105 transition-all shadow-md flex items-center gap-2 text-sm whitespace-nowrap">
            <Sparkles className="w-4 h-4" />
            Dùng thử Đậu miễn phí
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </Link>
      </div>
    </div>
  );
}
