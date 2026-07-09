"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { buyCreditsAPI } from "@/lib/api";
import { Check, FileText, Mic, Infinity, Shield, Zap, Sparkles, Wallet, HelpCircle, ChevronRight } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { CREDIT_PACKAGES, GENERAL_BENEFITS } from "@/lib/constants";

export default function BillingPage() {
  const { credits, refreshCredits } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loadingPackage, setLoadingPackage] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams.get("success") === "true") {
      toast.success("Nạp credits thành công! Số dư đã được cập nhật.");
      refreshCredits();
      // Remove query parameters from URL without refreshing
      router.replace("/app/billing");
    }
  }, [searchParams, refreshCredits, router]);

  const handlePurchase = (packageId: string) => {
    router.push(`/checkout?package_id=${packageId}`);
  };

  const benefitIcons = [
    <Sparkles key="1" size={20} className="text-emerald-600" />,
    <FileText key="2" size={20} className="text-emerald-600" />,
    <Mic key="3" size={20} className="text-emerald-600" />,
    <Infinity key="4" size={20} className="text-emerald-600" />,
    <Shield key="5" size={20} className="text-emerald-600" />,
    <Zap key="6" size={20} className="text-emerald-600" />,
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 font-sans text-(--fg)">
      
      {/* Wallet Card */}
      <div className="bg-white/80 backdrop-blur-md border border-[#2F4F4F]/10 rounded-3xl p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-sm mb-12">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-emerald-50 rounded-2xl flex items-center justify-center text-[var(--primary)] shadow-sm shrink-0">
            <Wallet size={28} />
          </div>
          <div>
            <h2 className="text-2xl font-heading font-black text-[#1A2D2D]">Ví Credits của bạn</h2>
            <p className="text-sm text-[var(--muted)] font-medium">
              Dùng để phân tích CV hoặc bắt đầu các buổi phỏng vấn giả định.
            </p>
          </div>
        </div>
        <div className="bg-white border border-[#2F4F4F]/10 px-8 py-4 rounded-2xl flex flex-col items-center justify-center shrink-0 min-w-[200px]">
          <span className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider mb-1">
            Số dư hiện tại
          </span>
          <span className="text-3xl font-heading font-black text-[#1A2D2D] flex items-center gap-2">
            {credits !== null ? credits : "—"}{" "}
            <span className="text-lg font-bold text-yellow-500">🪙</span>
          </span>
        </div>
      </div>

      {/* Package Header */}
      <div className="text-center mb-12">
        <h1 className="text-3xl md:text-[2.6rem] font-heading font-black text-[#1A2D2D] mb-4 tracking-tight leading-tight">
          Chọn gói tín dụng phù hợp
        </h1>
        <p className="text-sm md:text-base text-[#5A6D6D] max-w-xl mx-auto leading-relaxed font-medium">
          Đầu tư cho sự nghiệp của bạn với các gói tín dụng linh hoạt. Tín dụng được cộng ngay lập tức vào ví của bạn.
        </p>
      </div>

      {/* Grid of Credit Packages */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch max-w-7xl mx-auto mb-20">
        {CREDIT_PACKAGES.map((pkg) => (
          <div
            key={pkg.id}
            className={`bg-white border rounded-3xl p-6 relative flex flex-col justify-between transition-all duration-300 hover:shadow-md ${
              pkg.popular
                ? "border-[var(--primary)] shadow-[0_12px_40px_rgba(90,158,64,0.12)] scale-[1.02]"
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
                <span className="text-4xl font-heading font-black text-[#1A2D2D]">
                  {pkg.credits}
                </span>
                <span className="text-sm font-heading font-bold text-[#5A6D6D]">
                  tín dụng
                </span>
              </div>

              {/* Price Details */}
              <div className="text-2xl font-heading font-black text-[#1A2D2D] mb-6">
                {pkg.formattedPrice}
              </div>

              {/* Feature Checklist */}
              <ul className="space-y-4 mb-8 text-sm border-t border-[#2F4F4F]/5 pt-6">
                {pkg.features.map((feat, index) => (
                  <li key={index} className="flex items-center gap-2.5 leading-relaxed text-[#5A6D6D] font-medium">
                    <span className="w-5 h-5 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center shrink-0">
                      <Check size={12} className="text-slate-500" />
                    </span>
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* CTA Button */}
            <button
              onClick={() => handlePurchase(pkg.id)}
              disabled={loadingPackage !== null}
              className={`w-full py-3.5 px-4 font-heading font-extrabold rounded-2xl cursor-pointer transition-all duration-300 border flex items-center justify-center gap-1.5 ${
                pkg.popular
                  ? "bg-[var(--primary)] border-[var(--primary)] text-white hover:bg-[var(--primary)]/90 shadow-md shadow-[var(--primary)]/15"
                  : "bg-white border-[#2F4F4F]/15 text-[#1A2D2D] hover:bg-[#2F4F4F]/5 hover:border-[#2F4F4F]/30"
              }`}
            >
              {loadingPackage === pkg.id ? "Đang xử lý..." : "Mua ngay"}
              <ChevronRight size={16} />
            </button>
          </div>
        ))}
      </div>

      {/* Benefits Header */}
      <div className="text-center mb-12">
        <h3 className="text-2xl md:text-3xl font-heading font-black text-[#1A2D2D] tracking-tight">
          Mọi gói tín dụng đều bao gồm
        </h3>
      </div>

      {/* Unified Benefits Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6  mx-auto mb-20">
        {GENERAL_BENEFITS.map((benefit, index) => (
          <div 
            key={index}
            className="bg-white border border-[#2F4F4F]/10 rounded-2xl p-6 shadow-sm flex items-start gap-4 hover:shadow-md transition-shadow duration-300"
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
          </div>
        ))}
      </div>

      {/* Support Section */}
      <div className=" mx-auto border-t border-[#2F4F4F]/10 pt-10 flex flex-col md:flex-row items-center justify-between gap-6">
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
          <a 
            href="mailto:support@daucv.com"
            className="px-5 py-3 border border-[#2F4F4F]/15 hover:border-[#2F4F4F]/30 hover:bg-[#2F4F4F]/5 text-xs font-heading font-extrabold text-[#1A2D2D] rounded-xl transition-all duration-300"
          >
            Trung tâm trợ giúp
          </a>
          <a 
            href="https://m.me/10006767576576" 
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-3 text-xs font-heading font-extrabold text-[#1A2D2D] rounded-xl transition-all duration-300"
            style={{ backgroundColor: "rgba(90, 158, 64, 0.15)" }}
          >
            Liên hệ ngay
          </a>
        </div>
      </div>

    </div>
  );
}
