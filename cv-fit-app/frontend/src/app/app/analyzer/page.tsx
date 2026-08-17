"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Briefcase, Download, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import MatchDashboard from "@/components/workspace/MatchDashboard";
import DiffViewer from "@/components/workspace/DiffViewer";
import { DauOverloadScreen } from "@/components/magicpath/ai-overload-error-screen-dau/DauOverloadScreen";
import type { CVPipelineAnalysis, SuggestedEdit } from "@/types";
import {
  type ApiError,
  evaluateCVAPI,
  parseCVAPI,
  savePipelineTailoredCVAPI,
  tailorCVAPI,
} from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";
import { useWorkspace } from "@/context/WorkspaceContext";

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character] ?? character);
}

function tailoringChangesToSuggestedEdits(
  analysis: CVPipelineAnalysis,
): SuggestedEdit[] {
  return (analysis.tailoring?.change_log ?? []).map((change) => ({
    section: change.path.startsWith("research_experience")
      ? "Research experience"
      : "Experience",
    original_text: change.original_text,
    improved_safe: escapeHtml(change.proposed_text),
    improved_with_placeholders: escapeHtml(change.proposed_text),
    metric_questions: [],
    unsupported_assumptions: [],
    rewrite_risk: "safe",
    reason: change.rationale,
  }));
}

function pipelineExportErrorMessage(error: unknown): string {
  if (!error || typeof error !== "object" || !("status" in error) || !("message" in error)) {
    return apiErrorMessage(error);
  }
  const apiError = error as ApiError;
  if (apiError.status === 404) {
    return "Backend chưa tải chức năng xuất CV. Hãy khởi động lại backend rồi thử lại.";
  }
  try {
    const payload = JSON.parse(apiError.message) as {
      detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
    };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((issue) => {
          const field = issue.loc?.filter((part) => part !== "body").join(".");
          return [field, issue.msg].filter(Boolean).join(": ");
        })
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // Use the standard customer-safe fallback below.
  }
  return apiErrorMessage(error);
}

export default function AnalyzerPage() {
  const router = useRouter();
  const {
    cvText,
    jdText,
    hasData,
    isLoaded,
    cache,
    setCachedAnalysis,
    clearCache,
    rawExtractionRef,
  } = useWorkspace();

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CVPipelineAnalysis | null>(
    cache.analyzerResult // Initialize from cache
  );
  const [error, setError] = useState("");
  const [isTailoring, setIsTailoring] = useState(false);
  const [isSavingTailoredCV, setIsSavingTailoredCV] = useState(false);
  const [progressMessage, setProgressMessage] = useState("Đang gửi CV đến Bé Đậu...");
  const hasTriggered = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const cancelledByUserRef = useRef(false);
  const canonicalCVRef = useRef(cache.analyzerResult?.canonical_cv ?? null);

  // Route guard: redirect if no data
  useEffect(() => {
    if (isLoaded && !hasData) {
      router.replace("/app/setup");
    }
  }, [isLoaded, hasData, router]);

  // Auto-analyze on mount (only once, skip if cached)
  useEffect(() => {
    if (!hasData || hasTriggered.current || analysisResult) return;
    hasTriggered.current = true;

    const runAnalysis = async () => {
      const controller = new AbortController();
      abortControllerRef.current = controller;
      cancelledByUserRef.current = false;
      setIsAnalyzing(true);
      setError("");
      setProgressMessage(canonicalCVRef.current ? "Đang đánh giá CV..." : "Đang lập bản đồ CV...");
      try {
        const cached = cache.analyzerResult;
        let sourceDocument = cached?.source_document_v2;
        let sourceTicket = cached?.source_ticket;
        let canonicalCV = canonicalCVRef.current;

        if (!canonicalCV || !sourceDocument || !sourceTicket) {
          const parsed = await parseCVAPI(cvText, rawExtractionRef?.id, controller.signal);
          canonicalCV = parsed.canonical_cv;
          sourceDocument = parsed.source_document_v2;
          sourceTicket = parsed.source_ticket;
          canonicalCVRef.current = canonicalCV;
        }

        setProgressMessage(jdText.trim() ? "Đang đánh giá độ phù hợp với JD..." : "Đang đánh giá chất lượng CV...");
        const evaluation = await evaluateCVAPI(canonicalCV, jdText, controller.signal);

        setProgressMessage("Đang tối ưu các bullet CV an toàn...");
        let tailoring = cached?.tailoring;
        if (!tailoring) {
          try {
            tailoring = await tailorCVAPI(canonicalCV, jdText, evaluation, controller.signal);
          } catch (tailorErr) {
            console.warn("Tailoring failed, proceeding with evaluation only", tailorErr);
          }
        }

        const data = {
          canonical_cv: canonicalCV,
          source_document_v2: sourceDocument,
          source_ticket: sourceTicket,
          evaluation,
          tailoring,
        } satisfies CVPipelineAnalysis;
        setAnalysisResult(data);
        setCachedAnalysis(data);
      } catch (err: unknown) {
        const isAbort =
          cancelledByUserRef.current ||
          controller.signal.aborted ||
          (err instanceof Error && err.name === "AbortError") ||
          (err instanceof DOMException && err.name === "AbortError");

        if (isAbort) {
          setError("Bạn đã hủy phân tích CV.");
          return;
        }
        console.error(err);
        setError(pipelineExportErrorMessage(err));
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        setIsAnalyzing(false);
      }
    };

    runAnalysis();
  }, [
    hasData,
    cvText,
    jdText,
    rawExtractionRef,
    analysisResult,
    setCachedAnalysis,
    cache.analyzerResult,
  ]);

  const handleTailorCV = async () => {
    if (!analysisResult || isTailoring) return;
    const controller = new AbortController();
    abortControllerRef.current = controller;
    cancelledByUserRef.current = false;
    setIsTailoring(true);
    setProgressMessage("Đang tối ưu các bullet CV an toàn...");
    try {
      const tailoring = await tailorCVAPI(
        analysisResult.canonical_cv,
        jdText,
        analysisResult.evaluation,
        controller.signal,
      );
      const updated = { ...analysisResult, tailoring };
      setAnalysisResult(updated);
      setCachedAnalysis(updated);
      toast.success(
        tailoring.change_log.length > 0
          ? `Đã tạo ${tailoring.change_log.length} đề xuất tối ưu an toàn.`
          : "CV đã ổn; không cần thay đổi an toàn nào.",
      );
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      toast.error(apiErrorMessage(err));
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setIsTailoring(false);
    }
  };

  const handleSaveTailoredCV = async () => {
    if (!analysisResult || isSavingTailoredCV) return;
    if (
      !analysisResult.source_document_v2
      || analysisResult.source_document_v2.requires_reprocessing
      || !analysisResult.source_ticket
    ) {
      toast.info("Dữ liệu phân tích cũ không thể xuất CV. Đang phân tích lại từ nguồn CV.");
      handleReanalyze();
      return;
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    cancelledByUserRef.current = false;
    setIsSavingTailoredCV(true);
    setProgressMessage("Đang kiểm tra và lưu CV đã tối ưu...");
    try {
      let tailoring = analysisResult.tailoring;
      if (!tailoring) {
        tailoring = await tailorCVAPI(
          analysisResult.canonical_cv,
          jdText,
          analysisResult.evaluation,
          controller.signal,
        );
      }
      const version = await savePipelineTailoredCVAPI(
        cvText,
        rawExtractionRef?.id,
        jdText,
        analysisResult.source_document_v2,
        analysisResult.source_ticket,
        tailoring,
        "classic_ats",
        controller.signal,
      );
      toast.success("Đã lưu CV đã tối ưu. Đang chuyển sang màn hình xem trước & xuất PDF...");
      router.push(`/app/history?selected=${version.id}`);
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      toast.error(pipelineExportErrorMessage(err));
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setIsSavingTailoredCV(false);
    }
  };
  const handleReanalyze = () => {
    toast.info("Đang phân tích lại CV...");
    hasTriggered.current = false;
    canonicalCVRef.current = null;
    clearCache();
    setAnalysisResult(null);
    setError("");
    setIsAnalyzing(true);
  };

  const handleCancelAnalysis = () => {
    cancelledByUserRef.current = true;
    abortControllerRef.current?.abort();

    if (isTailoring || isSavingTailoredCV) {
      setIsTailoring(false);
      setIsSavingTailoredCV(false);
      setProgressMessage(isSavingTailoredCV ? "Đã hủy lưu CV." : "Đã hủy tối ưu CV.");
      toast.info(isSavingTailoredCV ? "Bạn đã hủy lưu CV." : "Bạn đã hủy tối ưu CV.");
      return;
    }

    setIsAnalyzing(false);
    setError("Bạn đã hủy phân tích CV.");
  };

  if (!isLoaded || !hasData) return null; // Will redirect via useEffect if isLoaded and no data

  return (
    <div className="relative">
      {(isAnalyzing || isTailoring || isSavingTailoredCV) && (
        <LoadingOverlay
          message={progressMessage}
          onCancel={handleCancelAnalysis}
        />
      )}

      {error && !isAnalyzing && !isTailoring && !isSavingTailoredCV && (
        <DauOverloadScreen message={error} onRetry={handleReanalyze} />
      )}

      {analysisResult && !isAnalyzing && !isTailoring && !isSavingTailoredCV && (
        <div className="flex flex-col pb-12">
          <MatchDashboard result={analysisResult.evaluation} />
          {analysisResult.tailoring && (
            <div id="diff-viewer" className="mt-2">
              {analysisResult.tailoring.change_log.length > 0 ? (
                <DiffViewer edits={tailoringChangesToSuggestedEdits(analysisResult)} language="vi" />
              ) : (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="rounded-3xl border border-emerald-100 bg-emerald-50/50 p-6 md:p-8 shadow-sm mb-8"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-9 h-9 bg-emerald-100 rounded-xl flex items-center justify-center">
                      <ShieldCheck size={20} className="text-emerald-700" />
                    </div>
                    <h2 className="text-base font-bold text-emerald-950">Đề xuất viết lại</h2>
                  </div>
                  <p className="text-sm leading-6 text-emerald-900">
                    {analysisResult.tailoring.tailoring_summary || "CV của bạn đã có cấu trúc và số liệu thực tế rõ ràng. Không cần thay đổi nào để đảm bảo tính an toàn và trung thực của CV."}
                  </p>
                </motion.div>
              )}
            </div>
          )}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-wrap gap-4 justify-center mt-4"
          >
            <button
              onClick={() => router.push("/app/jobs")}
              className="px-8 py-4 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-2xl font-semibold hover:scale-105 transition-all duration-300 shadow-lg flex items-center gap-2 cursor-pointer"
            >
              <Briefcase className="w-5 h-5" />
              Tìm việc phù hợp
            </button>
            {analysisResult.tailoring ? (
              <button
                onClick={handleSaveTailoredCV}
                disabled={isSavingTailoredCV}
                className="px-8 py-4 bg-[var(--primary)] text-white rounded-2xl font-semibold hover:scale-105 transition-all duration-300 shadow-lg flex items-center gap-2"
              >
                <Download className="w-5 h-5" />
                {isSavingTailoredCV ? "Đang lưu CV..." : "Lưu & xuất CV đã tối ưu"}
              </button>
            ) : (
              <button
                onClick={handleTailorCV}
                disabled={isTailoring}
                className="px-8 py-4 bg-[var(--primary)] text-white rounded-2xl font-semibold hover:scale-105 transition-all duration-300 shadow-lg flex items-center gap-2"
              >
                <Sparkles className="w-5 h-5" />
                {isTailoring ? "Đang tối ưu CV..." : "Tạo CV đã tối ưu"}
              </button>
            )}
            <button
              onClick={() => router.push("/app/setup")}
              className="px-8 py-4 bg-white text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all border-2 border-[var(--primary)]/20"
            >
              Phân tích CV khác
            </button>
          </motion.div>
        </div>
      )}


      <style>{`
        @media print {
          aside, header, nav { display: none !important; }
        }
      `}</style>
    </div>
  );
}
