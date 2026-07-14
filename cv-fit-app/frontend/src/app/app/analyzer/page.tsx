"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Briefcase } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import MatchDashboard from "@/components/workspace/MatchDashboard";
import DiffViewer from "@/components/workspace/DiffViewer";
import type { CVAnalysisResponse } from "@/types";
import { analyzeCVAPI, createTailoredCVVersionAPI } from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";
import { useWorkspace } from "@/context/WorkspaceContext";

export default function AnalyzerPage() {
  const router = useRouter();
  const { cvText, jdText, hasData, isLoaded, cache, setCachedAnalysis } = useWorkspace();

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CVAnalysisResponse | null>(
    cache.analyzerResult // Initialize from cache
  );
  const [error, setError] = useState("");
  const [isSavingTailoredCV, setIsSavingTailoredCV] = useState(false);
  const hasTriggered = useRef(false);

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
      setIsAnalyzing(true);
      setError("");
      try {
        const data = await analyzeCVAPI(cvText, jdText);
        setAnalysisResult(data);
        setCachedAnalysis(data); // Save to cache
      } catch (err: unknown) {
        console.error(err);
        setError(apiErrorMessage(err));
      } finally {
        setIsAnalyzing(false);
      }
    };

    runAnalysis();
  }, [hasData, cvText, jdText, analysisResult, setCachedAnalysis]);

  const handleCreateTailoredCV = async () => {
    if (!analysisResult?.tailored_cv) return;
    setIsSavingTailoredCV(true);
    try {
      const version = await createTailoredCVVersionAPI({
        tailored_cv: analysisResult.tailored_cv,
        source_cv_text: cvText,
        suggested_edits: analysisResult.suggested_edits,
        jd_text: jdText,
        target_role: analysisResult.target_role || undefined,
        company_name: analysisResult.company_name || undefined,
        selected_design: "classic_ats",
        tailoring_entitlement: analysisResult.tailoring_entitlement,
      });
      router.push(`/app/history?preview=${version.id}`);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setIsSavingTailoredCV(false);
    }
  };
  const handleReanalyze = () => {
    toast.info("Đang phân tích lại CV...");
    hasTriggered.current = false;
    setIsAnalyzing(true);
    setAnalysisResult(null);
    setError("");
  };

  if (!isLoaded || !hasData) return null; // Will redirect via useEffect if isLoaded and no data

  return (
    <div className="relative">
      {isAnalyzing && <LoadingOverlay />}

      {error && !isAnalyzing && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-600 font-medium">{error}</p>
          <button
            onClick={handleReanalyze}
            className="px-6 py-3 bg-[var(--primary)] text-white rounded-2xl font-semibold hover:scale-105 transition-all"
          >
            Thử lại
          </button>
        </div>
      )}

      {analysisResult && !isAnalyzing && (
        <div className="flex flex-col pb-12">
          <MatchDashboard result={analysisResult} />
          <div id="diff-viewer">
            <DiffViewer
              edits={analysisResult.suggested_edits}
              language={analysisResult.source_language ?? "vi"}
            />
          </div>
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
            <button
              onClick={handleCreateTailoredCV}
              disabled={isSavingTailoredCV}
              className="px-8 py-4 bg-[var(--primary)] text-white rounded-2xl font-semibold hover:scale-105 transition-all duration-300 shadow-lg flex items-center gap-2"
            >
              <Sparkles className="w-5 h-5" />
              {isSavingTailoredCV ? "Đang tạo CV..." : "Tạo CV đã tối ưu"}
            </button>
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
