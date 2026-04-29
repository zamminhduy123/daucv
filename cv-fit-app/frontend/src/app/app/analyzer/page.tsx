"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { motion } from "framer-motion";

import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import InputSection from "@/components/workspace/InputSection";
import MatchDashboard from "@/components/workspace/MatchDashboard";
import DiffViewer from "@/components/workspace/DiffViewer";
import SupportCard from "@/components/workspace/SupportCard";
import type { WorkspaceInputs, CVAnalysisResponse } from "@/types";
import { analyzeCVAPI } from "@/lib/api";

const EMPTY_INPUTS: WorkspaceInputs = { jdText: "", cvText: "", cvFile: null };

export default function AnalyzerPage() {
  const [currentView, setCurrentView] = useState<"input" | "results">("input");
  const [inputs, setInputs] = useState<WorkspaceInputs>(EMPTY_INPUTS);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [analysisResult, setAnalysisResult] = useState<CVAnalysisResponse | null>(null);

  const handleChange = (patch: Partial<WorkspaceInputs>) =>
    setInputs((prev) => ({ ...prev, ...patch }));

  const handleAnalyze = async () => {
    if (!inputs.jdText.trim()) { setError("Bạn chưa dán JD vào nhé!"); return; }
    if (!inputs.cvText.trim()) {
      setError("Bạn chưa có nội dung CV — dán text hoặc tải PDF!");
      return;
    }
    setError("");
    setIsAnalyzing(true);
    try {
      const data = await analyzeCVAPI(inputs.cvText, inputs.jdText);
      setAnalysisResult(data);
      setCurrentView("results");
    } catch (err: unknown) {
      console.error(err);
      setError("Lỗi từ server. Vui lòng thử lại!");
      alert("Lỗi từ server: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleBack = () => { setCurrentView("input"); setError(""); };
  const handleExportPDF = () => window.print();

  return (
    <div className="relative">
      {isAnalyzing && <LoadingOverlay />}

      {currentView === "input" && (
        <InputSection
          inputs={inputs}
          onChange={handleChange}
          onAnalyze={handleAnalyze}
          onInterview={() => {}}
          isAnalyzing={isAnalyzing}
          isStartingInterview={false}
          error={error}
        />
      )}

      {currentView === "results" && (
        <div className="flex flex-col pb-12">
          {analysisResult && (
            <>
              <MatchDashboard result={analysisResult} />
              <div id="diff-viewer">
                <DiffViewer edits={analysisResult.suggested_edits} />
              </div>
            </>
          )}
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
              onClick={handleBack}
              className="px-8 py-4 bg-white text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all border-2 border-[var(--primary)]/20"
            >
              Quay lại
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
