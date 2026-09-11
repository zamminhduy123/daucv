"use client";

import React, { useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Check, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/context/WorkspaceContext";
import { readWizardHandoff } from "@/lib/wizard-handoff";

interface StepItem {
  id: string;
  number: number;
  label: string;
  shortLabel: string;
  path: string;
}

const STEPS: StepItem[] = [
  { id: "setup", number: 1, label: "Chọn CV", shortLabel: "CV", path: "/app/setup" },
  { id: "review", number: 2, label: "Soát & Chỉnh sửa", shortLabel: "Soát lỗi", path: "/app/review" },
  { id: "analyzer", number: 3, label: "Phân tích & Tối ưu", shortLabel: "Phân tích", path: "/app/analyzer" },
  { id: "export", number: 4, label: "So sánh & Xuất PDF", shortLabel: "Xuất PDF", path: "/app/export" },
];

interface FlowStepIndicatorProps {
  compact?: boolean;
}

export default function FlowStepIndicator({ compact = false }: FlowStepIndicatorProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();
  const userId = (session?.user as { id?: string; email?: string } | undefined)?.id ?? session?.user?.email ?? null;

  const { hasData, selectedCvId, cache } = useWorkspace();

  const currentStepIndex = useMemo(() => {
    if (pathname.startsWith("/app/setup")) return 0;
    if (pathname.startsWith("/app/review")) return 1;
    if (pathname.startsWith("/app/analyzer")) return 2;
    if (pathname.startsWith("/app/export")) return 3;
    return -1;
  }, [pathname]);

  // If we are outside the 4-step wizard (e.g. jobs, history, settings), don't render
  if (currentStepIndex === -1) {
    return null;
  }

  const isStepAccessible = (index: number): boolean => {
    // Step 1 (Setup) is always accessible
    if (index === 0) return true;

    // Step 2 (Review) requires having CV data or an active CV selected
    if (index === 1) return Boolean(hasData || selectedCvId);

    // Step 3 (Analyzer) requires having cached analysis, or a fresh wizard handoff, or current >= 2
    if (index === 2) {
      if (currentStepIndex >= 2) return true;
      if (cache.analyzerResult) return true;
      const handoff = readWizardHandoff(userId);
      if (handoff && handoff.source_cv_id === selectedCvId) return true;
      return false;
    }

    // Step 4 (Export) requires having a tailored CV or being at step 4
    if (index === 3) {
      if (currentStepIndex >= 3) return true;
      if (cache.analyzerResult?.tailoring) return true;
      return false;
    }

    return false;
  };

  const handleStepClick = (index: number, step: StepItem) => {
    if (index === currentStepIndex) return;

    if (!isStepAccessible(index)) {
      if (index === 1) {
        toast.info("Vui lòng chọn hoặc tải lên một CV trước.");
      } else if (index === 2) {
        toast.info("Vui lòng duyệt thông tin CV ở bước Soát lỗi trước.");
      } else if (index === 3) {
        toast.info("Vui lòng phân tích và tạo CV tối ưu trước.");
      }
      return;
    }

    router.push(step.path);
  };

  if (compact) {
    return (
      <nav aria-label="Tiến trình làm việc" className="flex items-center gap-1.5">
        <div className="flex items-center gap-1.5 rounded-full bg-[#EAF5EC] px-3 py-1 text-xs font-bold text-[#2D7A58]">
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[#2D7A58] text-[10px] text-white">
            {currentStepIndex + 1}
          </span>
          <span>{STEPS[currentStepIndex]?.label}</span>
          <span className="text-[#2D7A58]/60 font-normal">({currentStepIndex + 1}/4)</span>
        </div>
      </nav>
    );
  }

  return (
    <nav aria-label="Tiến trình làm việc" className="flex items-center">
      {/* Mobile: compact badge */}
      <div className="flex md:hidden items-center gap-1.5 rounded-full bg-[#EAF5EC] px-3 py-1 text-xs font-bold text-[#2D7A58]">
        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[#2D7A58] text-[10px] text-white">
          {currentStepIndex + 1}
        </span>
        <span className="truncate max-w-[140px]">{STEPS[currentStepIndex]?.label}</span>
        <span className="text-[#2D7A58]/60 font-normal text-[11px]">(4 bước)</span>
      </div>

      {/* Desktop: connected stepper */}
      <ol className="hidden md:flex items-center gap-1 lg:gap-2">
        {STEPS.map((step, index) => {
          const isCurrent = index === currentStepIndex;
          const isCompleted = index < currentStepIndex;
          const accessible = isStepAccessible(index);

          return (
            <li key={step.id} className="flex items-center">
              <button
                type="button"
                onClick={() => handleStepClick(index, step)}
                disabled={!accessible && !isCurrent}
                aria-current={isCurrent ? "step" : undefined}
                className={`relative group flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-xs transition-all after:absolute after:-inset-2.5 after:content-[''] cursor-pointer ${
                  isCurrent
                    ? "bg-[#EAF5EC] font-bold text-[#2D7A58] shadow-2xs"
                    : isCompleted
                      ? "text-slate-700 font-semibold hover:bg-slate-100 hover:text-[#2D7A58]"
                      : accessible
                        ? "text-slate-600 font-medium hover:bg-slate-50 hover:text-slate-900"
                        : "text-slate-400 font-medium opacity-60 cursor-not-allowed"
                }`}
                title={
                  accessible
                    ? `Bước ${step.number}: ${step.label}`
                    : `Chưa hoàn thành các bước trước để vào ${step.label}`
                }
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] transition-colors ${
                    isCurrent
                      ? "bg-[#2D7A58] text-white font-bold"
                      : isCompleted
                        ? "bg-[#2D7A58]/15 text-[#2D7A58] font-bold"
                        : "bg-slate-100 text-slate-400 font-medium"
                  }`}
                >
                  {isCompleted ? <Check size={12} strokeWidth={2.8} /> : step.number}
                </span>
                <span className="hidden sm:inline">{step.label}</span>
                <span className="sm:hidden">{step.shortLabel}</span>
              </button>

              {index < STEPS.length - 1 && (
                <ChevronRight
                  size={13}
                  className={`mx-0.5 shrink-0 ${
                    index < currentStepIndex ? "text-[#2D7A58]/50" : "text-slate-300"
                  }`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
