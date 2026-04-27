"use client";

import { useState } from "react";
import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

import TopNavbar from "@/components/shared/TopNavbar";
import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import InputSection from "@/components/workspace/InputSection";
import MatchDashboard from "@/components/workspace/MatchDashboard";
import DiffViewer from "@/components/workspace/DiffViewer";
import InterviewRoom from "@/components/workspace/InterviewRoom";
import SupportCard from "@/components/workspace/SupportCard";
import type { WorkspaceInputs, CVAnalysisResponse } from "@/types";
import { analyzeCVAPI, sendInterviewChatAPI } from "@/lib/api";

const EMPTY_INPUTS: WorkspaceInputs = { jdText: "", cvText: "", cvFile: null };

/**
 * Workspace page — manages the 2-step flow state.
 * Uses h-screen + flex-col so the entire UI (including CTA) is always visible
 * without any page-level scroll.
 */
export default function WorkspacePage() {
  const [currentView, setCurrentView] = useState<'input' | 'analyze' | 'interview'>('input');
  const [inputs, setInputs] = useState<WorkspaceInputs>(EMPTY_INPUTS);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isStartingInterview, setIsStartingInterview] = useState(false);
  const [error, setError] = useState("");

  const [analysisResult, setAnalysisResult] = useState<CVAnalysisResponse | null>(null);
  const [interviewState, setInterviewState] = useState<unknown>(null);

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
      setCurrentView('analyze');
    } catch (err: unknown) {
      console.error(err);
      setError("Lỗi từ server. Vui lòng xem console hoặc thử lại!");
      alert("Lỗi từ server: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleBack = () => { setCurrentView('input'); setError(""); };
  const handleExportPDF = () => window.print();

  const handleInterview = async () => {
    if (!inputs.jdText.trim()) { setError("Bạn chưa dán JD vào nhé!"); return; }
    if (!inputs.cvText.trim()) { 
      setError("Bạn chưa có nội dung CV — dán text hoặc tải PDF!"); 
      return; 
    }
    setError("");
    setIsStartingInterview(true);

    try {
      const data = await sendInterviewChatAPI(inputs.jdText, inputs.cvText, []);
      setInterviewState(data);
      setCurrentView('interview');
    } catch (err: unknown) {
      console.error(err);
      setError("Lỗi bắt đầu phỏng vấn. Vui lòng xem console hoặc thử lại!");
      alert("Lỗi từ server: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsStartingInterview(false);
    }
  };

  return (
    // Lock entire layout to viewport height — no page scroll
    <div className="min-h-screen flex flex-col bg-[#F9F9F2] overflow-y-auto relative">
      {/* Decorative background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-20 w-96 h-96 bg-(--primary)/10 rounded-full blur-3xl z-0" />
        <div className="absolute bottom-40 left-20 w-96 h-96 bg-(--primary)/5 rounded-full blur-3xl z-0" />
      </div>

      {(isAnalyzing || isStartingInterview) && <LoadingOverlay />}

      {/* ── Sticky top nav ── */}
      <TopNavbar
        currentStep={currentView === 'input' ? 1 : 2}
        leftSlot={
          <Link
            href="/"
            className="flex items-center gap-1.5 text-sm font-semibold text-[#5A6D6D] no-underline hover:text-[#2F4F4F] transition-colors"
          >
            <ArrowLeft size={15} /> Trang chủ
          </Link>
        }
      />

      {/* ── Main content — fills remaining height, no outer scroll ── */}
      <main className="flex-1 flex flex-col px-6 py-4 max-w-7xl w-full mx-auto">

        {/* Step 1: Input workspace */}
        {currentView === 'input' && (
          <InputSection
            inputs={inputs}
            onChange={handleChange}
            onAnalyze={handleAnalyze}
            onInterview={handleInterview}
            isAnalyzing={isAnalyzing}
            isStartingInterview={isStartingInterview}
            error={error}
          />
        )}

        {/* Step 2: Results */}
        {currentView === 'analyze' && (
          <div className="flex flex-col gap-8 relative z-10 max-w-7xl w-full mx-auto pb-12">
            {/* Scrollable results area */}
            <div className="flex-1 pr-1" style={{ scrollbarWidth: "thin" }}>
              {analysisResult && (
                <>
                  <MatchDashboard result={analysisResult} />
                  <DiffViewer edits={analysisResult.suggested_edits} />
                </>
              )}
            </div>
                        {/* Support the Developer */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="mt-6 mb-8"
            >
              <SupportCard compact/>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="mt-4 flex flex-wrap gap-4 justify-center"
            >
              <button onClick={handleExportPDF} className="px-8 py-4 bg-(--primary) text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all duration-300 shadow-lg flex items-center gap-2">
                <Download className="w-5 h-5" />
                Lưu PDF
              </button>
              <button onClick={handleBack} className="px-8 py-4 bg-white text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all border-2 border-(--primary)/20 flex items-center gap-2">
                Quay lại
              </button>
            </motion.div>


          </div>
        )}

        {/* Step 3: Interview Room */}
        {currentView === 'interview' && (
          <InterviewRoom
            cvText={inputs.cvText}
            jdText={inputs.jdText}
            initialState={interviewState}
            onBack={handleBack}
          />
        )}
      </main>

      <style>{`
        @media print {
          header, nav { display: none !important; }
        }
      `}</style>
    </div>
  );
}
