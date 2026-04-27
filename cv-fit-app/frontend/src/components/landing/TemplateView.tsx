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
  ArrowRight
} from "lucide-react";
import { useState } from "react";
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "./Footer";
// CtaAndFooter import removed

// The data passed from server component
export type TemplateData = {
  name: string;
  title: string;
  subtitle: string;
  keywords: string[];
  proTips: Array<{ icon: string; title: string; description: string }>;
  template: {
    name: string;
    title: string;
    contact: string;
    summary: string;
    experience: Array<{ role: string; company: string; period: string; achievements: string[] }>;
    education: string;
    skills: string[];
  };
};

const IconMap: Record<string, React.ElementType> = {
  Target: Target,
  Zap: Zap,
  TrendingUp: TrendingUp,
  Sparkles: Sparkles,
};

export default function TemplateView({ data }: { data: TemplateData }) {
  const [copied, setCopied] = useState(false);

  const generateCVText = () => {
    const { template } = data;
    return `${template?.name || ""}
${template?.title || ""}
${template.contact}

SUMMARY
${template.summary}

SKILLS
${template.skills.join('\n')}

EXPERIENCE
${template.experience.map(exp => `
${exp.role} | ${exp.company} | ${exp.period}
${exp.achievements.map(a => `• ${a}`).join('\n')}
`).join('\n')}

EDUCATION
${template.education}`;
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(generateCVText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#F9F9F2]">
      {/* Decorative background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-40 right-20 w-96 h-96 bg-(--primary)/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-20 w-96 h-96 bg-(--primary)/10 rounded-full blur-3xl" />
      </div>

      <LandingNavbar />

      <div className="relative">
        {/* Hero Section */}
        <section className="px-6 py-16 lg:py-24">
          <div className="max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-12 items-center">
              {/* Left: Text */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.2 }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-(--primary)/10 rounded-full border-2 border-[var(--primary)]/20 mb-6"
                >
                  <Sparkles className="w-4 h-4 text-(--primary)" />
                  <span className="text-sm font-semibold text-[#2F4F4F]">Mẫu CV được tin dùng bởi 1000+ ứng viên</span>
                </motion.div>

                <h1
                  style={{
                    fontSize: 'clamp(2rem, 4vw, 3.5rem)',
                    lineHeight: 1.1,
                    fontWeight: 700,
                    color: '#2F4F4F'
                  }}
                  className="mb-6 font-heading"
                >
                  {data.title}
                </h1>

                <p className="text-lg text-[#5A6D6D] leading-relaxed mb-8">
                  {data.subtitle}
                </p>

                <div className="flex flex-wrap gap-4">
                  <Link href="/app">
                    <button className="group px-8 py-4 bg-(--primary) text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all shadow-lg hover:shadow-xl flex items-center gap-2">
                      Tùy chỉnh với AI
                      <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </button>
                  </Link>
                  <button
                    onClick={handleCopy}
                    className="px-8 py-4 bg-white text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all border-2 border-[var(--primary)]/20 flex items-center gap-2"
                  >
                    {copied ? (
                      <>
                        <CheckCircle className="w-5 h-5 text-(--primary)" />
                        Đã copy!
                      </>
                    ) : (
                      <>
                        <Copy className="w-5 h-5" />
                        Copy text mẫu
                      </>
                    )}
                  </button>
                </div>
              </motion.div>

              {/* Right: Mascot as Expert */}
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
                className="flex justify-center lg:justify-end"
              >
                <div className="relative">
                  <div className="absolute inset-0 bg-(--primary)/20 rounded-full blur-3xl scale-110" />
                  <div className="relative bg-white p-8 rounded-3xl border-2 border-[var(--primary)]/20 shadow-2xl flex flex-col items-center justify-center h-64 w-64">
                    <Image 
                      src="/main-icon.webp" 
                      alt="CV Expert Mascot" 
                      width={100} 
                      height={100} 
                      className="mb-4 drop-shadow-md"
                    />
                    <div className="mt-4 text-center">
                      <p className="font-semibold text-[#2F4F4F]">Bé Đậu - CV Expert</p>
                      <p className="text-sm text-[#5A6D6D]">Chuyên gia tối ưu CV</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Split Layout Content Area */}
        <section className="px-6 py-16">
          <div className="max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-5 gap-8">
              {/* Column 1: Pro Tips (2/5 width) */}
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
                className="lg:col-span-2"
              >
                <div className="sticky top-24">
                  <div className="mb-6">
                    <h2
                      style={{
                        fontSize: 'clamp(1.5rem, 3vw, 2rem)',
                        fontWeight: 700,
                        color: '#2F4F4F'
                      }}
                      className="mb-3 font-heading"
                    >
                      Bí quyết Đậu chia sẻ
                    </h2>
                    <p className="text-[#5A6D6D]">
                      Những insights từ 500+ CV được recruit phản hồi tích cực
                    </p>
                  </div>

                  <div className="space-y-6">
                    {data.proTips.map((tip, index) => {
                      const IconComp = IconMap[tip.icon] || Sparkles;
                      return (
                        <motion.div
                          key={index}
                          initial={{ opacity: 0, y: 20 }}
                          whileInView={{ opacity: 1, y: 0 }}
                          viewport={{ once: true }}
                          transition={{ delay: index * 0.1 }}
                          className="group bg-white p-6 rounded-3xl border-2 border-[var(--primary)]/10 hover:border-(--primary)/30 hover:shadow-lg transition-all duration-300"
                        >
                          <div className="flex items-start gap-4">
                            <div className="flex-shrink-0 w-12 h-12 bg-(--primary)/10 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                              <IconComp className="w-6 h-6 text-(--primary)" />
                            </div>
                            <div>
                              <h3 className="font-semibold text-[#2F4F4F] mb-2">{tip.title}</h3>
                              <p className="text-sm text-[#5A6D6D] leading-relaxed">
                                {tip.description}
                              </p>
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              </motion.div>

              {/* Column 2: Template Showcase (3/5 width) */}
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
                className="lg:col-span-3"
              >
                <div className="bg-white rounded-3xl shadow-2xl border-2 border-[var(--primary)]/10 overflow-hidden">
                  {/* Paper Header */}
                  <div className="bg-gradient-to-br from-[var(--primary)]/5 to-[var(--primary)]/10 px-8 py-6 border-b-2 border-[var(--primary)]/10">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-[#2F4F4F] mb-1">Template Preview</h3>
                        <p className="text-sm text-[#5A6D6D]">Mẫu CV chuẩn ATS cho {data.name}</p>
                      </div>
                      <button
                        onClick={handleCopy}
                        className="px-4 py-2 bg-white text-[#2F4F4F] rounded-xl font-medium hover:scale-105 transition-all border border-[var(--primary)]/20 flex items-center gap-2"
                      >
                        <Copy className="w-4 h-4" />
                        {copied ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  </div>

                  {/* CV Content - looks like a paper document */}
                  <div className="p-8 lg:p-12 bg-white text-left" style={{ fontFamily: 'Arial, sans-serif' }}>
                    {/* Header */}
                    <div className="text-center border-b-2 border-[#2F4F4F]/10 pb-6 mb-6">
                      <h1 className="text-3xl font-bold text-[#2F4F4F] mb-2">
                        {data.template.name}
                      </h1>
                      <p className="text-xl text-(--primary) font-semibold mb-3">
                        {data.template.title}
                      </p>
                      <p className="text-sm text-[#5A6D6D]">
                        {data.template.contact}
                      </p>
                    </div>

                    {/* Summary */}
                    <div className="mb-6">
                      <h2 className="text-lg font-bold text-[#2F4F4F] mb-3 uppercase tracking-wide border-l-4 border-[var(--primary)] pl-3">
                        Summary
                      </h2>
                      <p className="text-sm text-[#2F4F4F] leading-relaxed">
                        {data.template.summary}
                      </p>
                    </div>

                    {/* Skills */}
                    <div className="mb-6">
                      <h2 className="text-lg font-bold text-[#2F4F4F] mb-3 uppercase tracking-wide border-l-4 border-[var(--primary)] pl-3">
                        Skills
                      </h2>
                      <div className="space-y-2">
                        {data.template.skills.map((skill, index) => (
                          <p key={index} className="text-sm text-[#2F4F4F]">
                            • {skill}
                          </p>
                        ))}
                      </div>
                    </div>

                    {/* Experience */}
                    <div className="mb-6">
                      <h2 className="text-lg font-bold text-[#2F4F4F] mb-3 uppercase tracking-wide border-l-4 border-[var(--primary)] pl-3">
                        Experience
                      </h2>
                      <div className="space-y-5">
                        {data.template.experience.map((exp, index) => (
                          <div key={index}>
                            <div className="flex justify-between items-start mb-2">
                              <div>
                                <h3 className="font-bold text-[#2F4F4F]">{exp.role}</h3>
                                <p className="text-sm text-[#5A6D6D]">{exp.company}</p>
                              </div>
                              <p className="text-sm text-[#5A6D6D] italic">{exp.period}</p>
                            </div>
                            <ul className="space-y-1">
                              {exp.achievements.map((achievement, i) => (
                                <li key={i} className="text-sm text-[#2F4F4F] leading-relaxed">
                                  • {achievement}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Education */}
                    <div>
                      <h2 className="text-lg font-bold text-[#2F4F4F] mb-3 uppercase tracking-wide border-l-4 border-[var(--primary)] pl-3">
                        Education
                      </h2>
                      <p className="text-sm text-[#2F4F4F]">
                        {data.template.education}
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        <Footer/>

        {/* Conversion CTA - Floating Bottom Bar */}
        <motion.div
          initial={{ opacity: 0, y: 100 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="sticky bottom-0 z-40"
        >
          <div className="bg-gradient-to-br from-[var(--primary)] to-[var(--primary)]/90 border-t-4 border-white shadow-2xl">
            <div className="max-w-7xl mx-auto px-6 py-5">
              <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
                <div className="text-center lg:text-left">
                  <h3 className="text-2xl font-bold text-[#2F4F4F] mb-1">
                    Đừng copy máy móc. Hãy để AI làm việc cho bạn.
                  </h3>
                  <p className="text-[#2F4F4F]/80">
                    Bé Đậu sẽ tinh chỉnh mẫu CV này khớp 100% với Job Description của bạn trong 5 giây.
                  </p>
                </div>
                <Link href="/app">
                  <button className="group px-10 py-5 bg-white text-[#2F4F4F] rounded-2xl font-bold hover:scale-105 transition-all shadow-xl hover:shadow-2xl flex items-center gap-3 whitespace-nowrap">
                    <Sparkles className="w-6 h-6 text-(--primary)" />
                    Dùng thử Đậu miễn phí
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </Link>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
