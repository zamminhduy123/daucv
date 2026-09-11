"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Briefcase, Download, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { motion } from "motion/react";

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
import { clearWizardHandoff, readWizardHandoff } from "@/lib/wizard-handoff";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useAuth } from "@/context/AuthContext";

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
    selectedCvId,
  } = useWorkspace();
  const { refreshCredits, userId } = useAuth();

  // Wizard handoff: the review page persists the user-corrected document,
  // mints a source ticket for it, and stashes both in a user-scoped
  // sessionStorage entry before navigating here. The analyzer then skips
  // /api/cv/parse (LLM1) and its credit charge entirely. The handoff is
  // validated against the selected CV so a stale one can never apply to a
  // different CV; it is cleared once the analysis succeeds.
  const wizardHandoff = useMemo(
    () => {
      const handoff = readWizardHandoff(userId);
      return handoff && handoff.source_cv_id === selectedCvId ? handoff : null;
    },
    [userId, selectedCvId],
  );

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

  // Route guard: force user through Setup -> Review -> Analyzer flow
  useEffect(() => {
    if (!isLoaded) return;
    if (!hasData) {
      router.replace("/app/setup");
      return;
    }
    // Cannot analyze directly without having gone through the review wizard or having a cached analysis
    if (!analysisResult && !cache.analyzerResult && !wizardHandoff) {
      router.replace("/app/review");
      return;
    }
  }, [isLoaded, hasData, analysisResult, cache.analyzerResult, wizardHandoff, router]);

  // Auto-analyze on mount (only once, skip if cached or unreviewed)
  useEffect(() => {
    if (!hasData || hasTriggered.current || analysisResult) return;
    if (!cache.analyzerResult && !wizardHandoff) return;
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
        // Atomic + freshest-first: the wizard handoff is minted seconds ago
        // in review; a stale cache entry must never supply half the pair.
        // Mixing a cached document with a handoff ticket (or vice versa)
        // fails ticket verification with "no longer matches this CV".
        const useHandoffPair = Boolean(
          wizardHandoff?.source_document_v2 && wizardHandoff?.source_ticket,
        );
        let sourceDocument = useHandoffPair
          ? wizardHandoff?.source_document_v2 ?? null
          : cached?.source_document_v2 ?? wizardHandoff?.source_document_v2 ?? null;
        let sourceTicket = useHandoffPair
          ? wizardHandoff?.source_ticket ?? null
          : cached?.source_ticket ?? wizardHandoff?.source_ticket ?? null;
        let canonicalCV = useHandoffPair
          ? wizardHandoff?.canonical_cv ?? null
          : canonicalCVRef.current ?? wizardHandoff?.canonical_cv ?? null;

        // Wizard path: the document is already user-corrected and ticketed.
        // Skip parseCVAPI (LLM1) and its credit charge.
        if (!canonicalCV || !sourceDocument || !sourceTicket) {
          const parsed = await parseCVAPI(cvText, rawExtractionRef?.id, controller.signal);
          canonicalCV = parsed.canonical_cv;
          sourceDocument = parsed.source_document_v2;
          sourceTicket = parsed.source_ticket;
        }
        canonicalCVRef.current = canonicalCV;

        setProgressMessage(jdText.trim() ? "Đang đánh giá độ phù hợp với JD..." : "Đang đánh giá chất lượng CV...");
        const evaluation = await evaluateCVAPI(canonicalCV, jdText, controller.signal);

        setProgressMessage("Đang tối ưu các bullet CV an toàn...");
        // A fresh handoff means a (possibly edited) new document: never reuse
        // tailoring generated for a previous document's bullets.
        let tailoring = useHandoffPair ? undefined : cached?.tailoring;
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
        clearWizardHandoff(userId);
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
        void refreshCredits().catch(() => null);
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
    refreshCredits,
    wizardHandoff,
    userId,
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
    // Stale-doc guard: documents saved before review attestation existed
    // can never pass the server gate. Redirect to review instead of
    // failing with a cryptic 422.
    const srcDoc = analysisResult.source_document_v2;
    if (
      (srcDoc?.reconstruction_warnings ?? []).includes("missing_line_provenance") &&
      !srcDoc?.review_attested
    ) {
      toast.error("Bản CV này chưa được duyệt. Quay lại Review, bấm Lưu & Tiếp tục, rồi lưu lại.");
      router.push("/app/review");
      return;
    }
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
        wizardHandoff?.design ?? "classic_ats",
        controller.signal,
        wizardHandoff?.source_cv_id ?? selectedCvId ?? undefined,
      );
      toast.success("Đã lưu CV đã tối ưu. Đang mở màn hình so sánh & xuất PDF...");
      router.push(`/app/export?selected=${version.id}`);
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
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
            className="flex flex-wrap items-center justify-center gap-3.5 mt-6"
          >
            {analysisResult.tailoring ? (
              <button
                type="button"
                onClick={handleSaveTailoredCV}
                disabled={isSavingTailoredCV}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#2D7A58] px-8 py-3.5 text-base font-bold text-white shadow-md transition-all hover:bg-[#246347] active:scale-[0.98] disabled:opacity-60 cursor-pointer"
              >
                <Download className="w-5 h-5" />
                {isSavingTailoredCV ? "Đang lưu CV..." : "Lưu & xuất CV đã tối ưu"}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleTailorCV}
                disabled={isTailoring}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#2D7A58] px-8 py-3.5 text-base font-bold text-white shadow-md transition-all hover:bg-[#246347] active:scale-[0.98] disabled:opacity-60 cursor-pointer"
              >
                <Sparkles className="w-5 h-5" />
                {isTailoring ? "Đang tối ưu CV..." : "Tạo CV đã tối ưu"}
              </button>
            )}
            <button
              type="button"
              onClick={() => router.push("/app/jobs")}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-300 bg-white px-6 py-3.5 text-sm font-semibold text-emerald-800 shadow-sm transition-all hover:bg-emerald-50 active:scale-[0.98] cursor-pointer"
            >
              <Briefcase className="w-4 h-4 text-emerald-700" />
              Tìm việc phù hợp
            </button>
            <button
              type="button"
              onClick={() => router.push("/app/setup")}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-6 py-3.5 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50 active:scale-[0.98] cursor-pointer"
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
