"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Download } from "lucide-react";
import { motion } from "framer-motion";

import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import MatchDashboard from "@/components/workspace/MatchDashboard";
import DiffViewer from "@/components/workspace/DiffViewer";
import SupportCard from "@/components/workspace/SupportCard";
import type { CVAnalysisResponse } from "@/types";
import { analyzeCVAPI } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

export default function AnalyzerPage() {
  const router = useRouter();
  const { cvText, jdText, hasData } = useWorkspace();

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CVAnalysisResponse | null>(null);
  const [error, setError] = useState("");
  const hasTriggered = useRef(false);

  // Route guard: redirect if no data
  useEffect(() => {
    if (!hasData) {
      router.replace("/app/setup");
    }
  }, [hasData, router]);

  // Auto-analyze on mount (only once)
  useEffect(() => {
    if (!hasData || hasTriggered.current || analysisResult) return;
    hasTriggered.current = true;

    const runAnalysis = async () => {
      setIsAnalyzing(true);
      setError("");
      try {
        const data = await analyzeCVAPI(cvText, jdText);
        setAnalysisResult(data);
      } catch (err: unknown) {
        console.error(err);
        setError("Lỗi từ server. Vui lòng thử lại!");
      } finally {
        setIsAnalyzing(false);
      }
    };

    runAnalysis();
  }, [hasData, cvText, jdText, analysisResult]);

  const handleExportPDF = () => window.print();
  const handleReanalyze = async () => {
    hasTriggered.current = false;
    setAnalysisResult(null);
    setError("");
  };

  if (!hasData) return null; // Will redirect via useEffect

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
            <DiffViewer edits={analysisResult.suggested_edits} />
          </div>
          <SupportCard compact />
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-wrap gap-4 justify-center mt-4"
          >
            <button
              onClick={handleExportPDF}
              className="px-8 py-4 bg-[var(--primary)] text-white rounded-2xl font-semibold hover:scale-105 transition-all duration-300 shadow-lg flex items-center gap-2"
            >
              <Download className="w-5 h-5" />
              Lưu PDF
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
