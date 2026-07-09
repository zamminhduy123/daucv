"use client";

import React from "react";
import Link from "next/link";
import { Check, FileText, Mic, Infinity, Shield, Zap, Sparkles, HelpCircle, ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

import { CREDIT_PACKAGES, GENERAL_BENEFITS } from "@/lib/constants";

export default function PricingSection() {
  const shouldReduceMotion = useReducedMotion();
  const benefitIcons = [
    <Sparkles key="1" size={20} className="text-emerald-600" />,
    <FileText key="2" size={20} className="text-emerald-600" />,
    <Mic key="3" size={20} className="text-emerald-600" />,
    <Infinity key="4" size={20} className="text-emerald-600" />,
    <Shield key="5" size={20} className="text-emerald-600" />,
    <Zap key="6" size={20} className="text-emerald-600" />,
  ];

  return (
    <section id="pricing" className="py-24 bg-[var(--bg)] font-sans text-[var(--fg)] relative overflow-hidden">
      {/* Decorative Blur Backgrounds */}
      <div 
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full filter blur-[150px] pointer-events-none opacity-30"
        style={{ backgroundColor: "rgba(90, 158, 64, 0.12)" }}
      ></div>

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        
        {/* Title Header */}
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          <h2 className="text-3xl md:text-[2.6rem] font-heading font-black text-[#1A2D2D] mb-4 tracking-tight leading-tight">
            Có quá nhiều JD khác nhau?<br/>Mua thêm credits để tiếp tục tối ưu hồ sơ nào.
          </h2>
          <p className="text-sm md:text-base text-[#5A6D6D] mx-auto leading-relaxed">
            Đầu tư cho sự nghiệp của bạn với các gói tín dụng linh hoạt. Tín dụng được cộng ngay lập tức vào ví của bạn.
          </p>
        </motion.div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch max-w-5xl mx-auto mb-20">
          {CREDIT_PACKAGES.map((pkg, index) => (
            <motion.div
              key={pkg.id}
              initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: shouldReduceMotion ? 0 : index * 0.15, ease: "easeOut" }}
              whileHover={shouldReduceMotion ? {} : { 
                y: -8, 
                scale: pkg.popular ? 1.04 : 1.02,
                boxShadow: "0 20px 40px rgba(0, 0, 0, 0.08)"
              }}
              className={`bg-white border rounded-3xl p-8 relative flex flex-col justify-between transition-all duration-300 ${
                pkg.popular
                  ? "border-[var(--primary)] shadow-[0_12px_40px_rgba(90,158,64,0.12)]"
                  : "border-[#2F4F4F]/10 shadow-sm"
              }`}
            >
              <div>
                {/* Badge Top Header */}
                <div className="flex items-center justify-between mb-6 min-h-[30px]">
                  <span className={`text-[10px] md:text-xs uppercase tracking-wider px-3.5 py-1.5 rounded-full font-bold ${pkg.tierBadgeBg}`}>
                    {pkg.tierBadge}
                  </span>
                  {pkg.savingBadge && (
                    <span className="text-[10px] md:text-xs bg-emerald-50 text-emerald-700 font-extrabold px-3 py-1 rounded-full border border-emerald-100">
                      {pkg.savingBadge}
                    </span>
                  )}
                </div>

                {/* Credits quantity */}
                <div className="flex items-baseline gap-1.5 mb-2 mt-2">
                  <span className="text-5xl font-heading font-black text-[#1A2D2D]">
                    {pkg.credits}
                  </span>
                  <span className="text-lg font-heading font-bold text-[#5A6D6D]">
                    tín dụng
                  </span>
                </div>

                {/* Total Price */}
                <div className="text-3xl font-heading font-black text-[#1A2D2D] mb-6">
                  {pkg.formattedPrice}
                </div>

                {/* Feature Checklist */}
                <ul className="space-y-4 mb-8 text-sm border-t border-[#2F4F4F]/5 pt-6">
                  {pkg.features.map((feat, index) => (
                    <li key={index} className="flex items-center gap-3 text-[#5A6D6D] font-medium">
                      <span className="w-5 h-5 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center shrink-0">
                        <Check size={12} className="text-slate-500" />
                      </span>
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Mua ngay button */}
              <Link
                href="/app/billing"
                className={`w-full py-4 px-6 font-heading font-extrabold rounded-2xl text-center no-underline transition-all duration-300 flex items-center justify-center gap-1.5 cursor-pointer border ${
                  pkg.popular
                    ? "bg-[var(--primary)] border-[var(--primary)] text-white hover:bg-[var(--primary)]/90 shadow-md shadow-[var(--primary)]/15"
                    : "bg-white border-[#2F4F4F]/15 hover:border-[#2F4F4F]/30 text-[#1A2D2D] hover:bg-[#2F4F4F]/5"
                }`}
              >
                Mua ngay
                <ChevronRight size={16} />
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Benefits Header */}
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <h3 className="text-2xl md:text-3xl font-heading font-black text-[#1A2D2D] tracking-tight">
            Mọi gói tín dụng đều bao gồm
          </h3>
        </motion.div>

        {/* Unified Benefits Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-20">
          {GENERAL_BENEFITS.map((benefit, index) => (
            <motion.div 
              key={index}
              initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.5, delay: shouldReduceMotion ? 0 : index * 0.08, ease: "easeOut" }}
              whileHover={shouldReduceMotion ? {} : { 
                y: -4, 
                boxShadow: "0 10px 20px rgba(0, 0, 0, 0.04)"
              }}
              className="bg-white border border-[#2F4F4F]/10 rounded-2xl p-6 shadow-sm flex items-start gap-4 transition-colors duration-300"
            >
              <div 
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ backgroundColor: "rgba(9, 172, 90, 0.06)" }}
              >
                {benefitIcons[index]}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="font-heading font-bold text-sm md:text-base text-[#1A2D2D] leading-tight">
                  {benefit.title}
                </span>
                <span className="text-[11px] md:text-xs text-[#5A6D6D] mt-2 leading-relaxed font-medium">
                  {benefit.description}
                </span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Support Section */}
        {/* <motion.div
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="max-w-5xl mx-auto border-t border-[#2F4F4F]/10 pt-10 flex flex-col md:flex-row items-center justify-between gap-6"
        >
          <div className="text-center md:text-left flex flex-col">
            <h4 className="font-heading font-extrabold text-lg text-[#1A2D2D] flex items-center justify-center md:justify-start gap-2">
              <HelpCircle className="text-[var(--primary)]" size={20} />
              Bạn cần hỗ trợ?
            </h4>
            <p className="text-xs md:text-sm text-[#5A6D6D] mt-1.5 leading-relaxed font-medium max-w-lg">
              Đội ngũ của chúng tôi luôn sẵn sàng giải đáp thắc mắc về các gói tín dụng và cách thanh toán.
            </p>
          </div>
          <div className="flex flex-wrap gap-4 shrink-0 justify-center">
            <Link 
              href="mailto:support@daucv.com"
              className="px-5 py-3 border border-[#2F4F4F]/15 hover:border-[#2F4F4F]/30 hover:bg-[#2F4F4F]/5 text-xs font-heading font-extrabold text-[#1A2D2D] rounded-xl transition-all duration-300"
            >
              Trung tâm trợ giúp
            </Link>
            <Link 
              href="https://m.me/10006767576576" 
              target="_blank"
              className="px-5 py-3 text-xs font-heading font-extrabold text-[#1A2D2D] rounded-xl transition-all duration-300"
              style={{ backgroundColor: "rgba(90, 158, 64, 0.15)" }}
            >
              Liên hệ ngay
            </Link>
          </div>
        </motion.div> */}

      </div>
    </section>
  );
}
