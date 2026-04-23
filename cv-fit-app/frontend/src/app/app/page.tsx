"use client";

import { useState } from "react";
import { ArrowLeft, Download, Coffee } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

import TopNavbar from "@/components/shared/TopNavbar";
import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import InputSection from "@/components/workspace/InputSection";
import MatchDashboard from "@/components/workspace/MatchDashboard";
import DiffViewer from "@/components/workspace/DiffViewer";
import type { WorkspaceStep, WorkspaceInputs, CVAnalysisResponse } from "@/types";

const EMPTY_INPUTS: WorkspaceInputs = { jdText: "", cvText: "", cvFile: null };

/**
 * Workspace page — manages the 2-step flow state.
 * Uses h-screen + flex-col so the entire UI (including CTA) is always visible
 * without any page-level scroll.
 */
export default function WorkspacePage() {
  const [step, setStep] = useState<WorkspaceStep>(1);
  const [inputs, setInputs] = useState<WorkspaceInputs>(EMPTY_INPUTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [analysisResult, setAnalysisResult] = useState<CVAnalysisResponse | null>(null);

  const handleChange = (patch: Partial<WorkspaceInputs>) =>
    setInputs((prev) => ({ ...prev, ...patch }));

  const handleAnalyze = async () => {
    if (!inputs.jdText.trim()) { setError("Bạn chưa dán JD vào nhé!"); return; }
    if (!inputs.cvText.trim() && !inputs.cvFile) { 
      setError("Bạn chưa có nội dung CV — dán text hoặc tải PDF!"); 
      return; 
    }
    setError("");
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("jd_text", inputs.jdText);
      if (inputs.cvFile) {
        formData.append("file", inputs.cvFile);
      } else if (inputs.cvText) {
        formData.append("cv_text", inputs.cvText);
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/analyze-cv`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data: CVAnalysisResponse = await res.json();
      setAnalysisResult(data);
      setStep(2);
    } catch (err: any) {
      console.error(err);
      setError("Lỗi từ server. Vui lòng xem console hoặc thử lại!");
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => { setStep(1); setError(""); };
  const handleExportPDF = () => window.print();

  return (
    // Lock entire layout to viewport height — no page scroll
    <div className="min-h-screen flex flex-col bg-[#F9F9F2] overflow-y-auto relative">
      {/* Decorative background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-20 w-96 h-96 bg-[#98C18E]/10 rounded-full blur-3xl z-0" />
        <div className="absolute bottom-40 left-20 w-96 h-96 bg-[#98C18E]/5 rounded-full blur-3xl z-0" />
      </div>

      {loading && <LoadingOverlay />}

      {/* ── Sticky top nav ── */}
      <TopNavbar
        currentStep={step}
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
        {step === 1 && (
          <InputSection
            inputs={inputs}
            onChange={handleChange}
            onAnalyze={handleAnalyze}
            loading={loading}
            error={error}
          />
        )}

        {/* Step 2: Results */}
        {step === 2 && (
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

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="mt-4 flex flex-wrap gap-4 justify-center"
            >
              <button onClick={handleExportPDF} className="px-8 py-4 bg-[#98C18E] text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all duration-300 shadow-lg flex items-center gap-2">
                <Download className="w-5 h-5" />
                Lưu PDF
              </button>
              <button onClick={handleBack} className="px-8 py-4 bg-white text-[#2F4F4F] rounded-2xl font-semibold hover:scale-105 transition-all border-2 border-[#98C18E]/20 flex items-center gap-2">
                Thử JD khác
              </button>
            </motion.div>

            {/* Support the Developer */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="mt-6 mb-8"
            >
              <div className="bg-gradient-to-br from-[#B22222] to-[#B22222]/80 rounded-3xl p-8 text-center text-white relative overflow-hidden shadow-lg">
                <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full blur-2xl flex-shrink-0" />
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/10 rounded-full blur-2xl flex-shrink-0" />

                <div className="relative z-10">
                  <h3 className="text-2xl font-bold mb-3">Tiếp thêm may mắn cho Đậu?</h3>
                  <p className="mb-6 text-white/90 max-w-2xl mx-auto">
                    Bé Đậu đã nỗ lực hết mình để giúp bạn có một CV "nét". 
                    Nếu bạn thấy hữu ích, hãy tặng Admin một bát Chè Đậu Đỏ để giữ lấy may mắn cho vòng phỏng vấn sắp tới nhé!
                  </p>
                  <button className="px-8 py-4 bg-white text-[#B22222] rounded-2xl font-semibold hover:scale-105 transition-all inline-flex items-center gap-2 shadow-lg">
                    <Coffee className="w-5 h-5" />
                    Tặng Chè Đậu Đỏ (20k) 🍵
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
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
