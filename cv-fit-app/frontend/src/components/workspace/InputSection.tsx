"use client";

import { useRef, useState } from "react";
import { Upload, FileText, X, CheckCircle, AlertTriangle, Sparkles, Mic, Loader2, PenTool, Briefcase } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { WorkspaceInputs } from "@/types";
import { wordCount } from "@/lib/utils";
import { extractPdfAPI } from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";
import { useToast } from "@/components/ui/use-toast";

interface InputSectionProps {
  inputs: WorkspaceInputs;
  onChange: (patch: Partial<WorkspaceInputs>) => void;
  onAnalyze: () => void;
  onInterview: () => void;
  onWrite: () => void;
  onSearchJobs: () => void;
  isAnalyzing: boolean;
  isStartingInterview: boolean;
  isWriting: boolean;
  error: string;
}

// ── Sub-component: textarea card shell ────────────────────────────────────────
interface TextCardProps {
  title: React.ReactNode;
  subtitle: string;
  children: React.ReactNode;
  wordCountText: string;
  headerRight?: React.ReactNode;
  topBadge?: React.ReactNode;
}

function TextCard({ title, subtitle, children, wordCountText, headerRight, topBadge }: TextCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-[#2F4F4F]/8 shadow-sm flex flex-col overflow-hidden h-full">
      {/* Header — compact */}
      <div className="px-4 py-3 border-b border-[#2F4F4F]/[0.07] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: "rgba(152,193,142,0.15)" }}>
            <FileText size={15} color="var(--primary)" />
          </div>
          <div>
            <h2 className="font-heading font-bold text-[#2F4F4F] text-sm leading-tight">{title}</h2>
            <p className="text-[10px] text-[#5A6D6D]">{subtitle}</p>
          </div>
        </div>
        {headerRight}
      </div>

      {/* Optional badge */}
      {topBadge && <div className="mx-4 mt-2 shrink-0">{topBadge}</div>}

      {/* Textarea area — grows to fill remaining height */}
      <div className="flex flex-col flex-1 overflow-hidden">{children}</div>

      {/* Footer */}
      <div className="px-4 py-1.5 border-t border-[#2F4F4F]/6 bg-[#FAFAFA] shrink-0">
        <span className="text-[10px] text-[#5A6D6D]">{wordCountText}</span>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function InputSection({ 
  inputs, 
  onChange, 
  onAnalyze, 
  onInterview, 
  onWrite,
  onSearchJobs,
  isAnalyzing, 
  isStartingInterview, 
  isWriting,
  error 
}: InputSectionProps) {
  const cvFileInputRef = useRef<HTMLInputElement>(null);
  const jdFileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState<"cv" | "jd" | null>(null);
  const [isExtractingPDF, setIsExtractingPDF] = useState({ cv: false, jd: false });
  const [extractErrors, setExtractErrors] = useState({ cv: "", jd: "" });
  const { toast } = useToast();

  const setExtracting = (target: "cv" | "jd", value: boolean) => {
    setIsExtractingPDF((prev) => ({ ...prev, [target]: value }));
  };

  const setExtractError = (target: "cv" | "jd", value: string) => {
    setExtractErrors((prev) => ({ ...prev, [target]: value }));
  };

  const clearPdfInputValue = (target: "cv" | "jd") => {
    const ref = target === "cv" ? cvFileInputRef : jdFileInputRef;
    if (ref.current) ref.current.value = "";
  };

  const updatePdfTarget = (target: "cv" | "jd", file: File | null, text?: string) => {
    if (target === "cv") {
      onChange({ cvFile: file, ...(text !== undefined ? { cvText: text } : {}) });
    } else {
      onChange({ jdFile: file, ...(text !== undefined ? { jdText: text } : {}) });
    }
  };

  const handleFile = async (file: File, target: "cv" | "jd") => {
    const label = target === "cv" ? "CV" : "JD";

    if (file.type !== "application/pdf") {
      updatePdfTarget(target, null, "");
      clearPdfInputValue(target);
      setExtractError(target, `${label}: Vui lòng tải lên file PDF.`);
      return;
    }
    
    updatePdfTarget(target, file);
    setExtractError(target, "");
    setExtracting(target, true);

    try {
      const result = await extractPdfAPI(file);
      if (result.error) {
        setExtractError(target, `${label}: Đã có lỗi xảy ra khi trích xuất, vui lòng thử lại.`);
        console.error(result.error);
        updatePdfTarget(target, null, "");
        clearPdfInputValue(target);
      } else {
        updatePdfTarget(target, file, result.text || "");
      }
    } catch (err: unknown) {
      updatePdfTarget(target, null, "");
      clearPdfInputValue(target);
      setExtractError(target, `${label}: ${apiErrorMessage(err)}`);
      console.error(err);
    } finally {
      setExtracting(target, false);
    }
  };

  const handleDrop = (e: React.DragEvent, target: "cv" | "jd") => {
    e.preventDefault();
    setDragging(null);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file, target);
  };

  const clearFile = (target: "cv" | "jd") => {
    updatePdfTarget(target, null, "");
    setExtractError(target, "");
    clearPdfInputValue(target);
  };

  const handleAnalyzeClick = () => {
    if (!inputs.cvText.trim()) {
        toast({
            title: "Thiếu thông tin ⚠️",
            description: "Vui lòng tải lên hoặc dán nội dung CV của bạn trước khi tiếp tục.",
            variant: "destructive"
        });
        return;
    }
    onAnalyze();
  };

  const handleInterviewClick = () => {
    if (!inputs.cvText.trim()) {
        toast({
            title: "Thiếu thông tin ⚠️",
            description: "Vui lòng tải lên hoặc dán nội dung CV của bạn trước khi tiếp tục.",
            variant: "destructive"
        });
        return;
    }
    onInterview();
  };

  const handleWriteClick = () => {
    if (!inputs.cvText.trim()) {
        toast({
            title: "Thiếu thông tin ⚠️",
            description: "Vui lòng tải lên hoặc dán nội dung CV của bạn trước khi tiếp tục.",
            variant: "destructive"
        });
        return;
    }
    onWrite();
  };

  const isCvReady = inputs.cvText.trim().length > 20;

  return (
    // Full-height flex column on desktop, auto-height on mobile
    <div className="flex flex-col gap-3 md:gap-4 h-auto md:h-[calc(100vh-100px)]">

      {/* ── Compact page header ── */}
      <div className="shrink-0">
        <h1 className="font-heading font-bold text-[#2F4F4F] text-xl leading-tight">
          Không gian làm việc
        </h1>
        <p className="text-[#5A6D6D] text-sm mt-0.5">
          Dán JD và CV của bạn vào đây.{" "}
          <span className="text-(--primary) font-semibold">Bé Đậu sẽ lo phần còn lại.</span>
        </p>
      </div>

      {/* ── 2-col card grid — stacks on mobile, side-by-side on larger screens ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 flex-none md:flex-1">

                {/* RIGHT: CV */}
        <TextCard
          title={<>CV của bạn <span className="text-red-500 font-normal text-xs ml-1">(Yêu cầu)</span></>}
          subtitle="Dán text hoặc upload PDF"
          wordCountText={wordCount(inputs.cvText)}
          headerRight={
            <button
              onClick={() => cvFileInputRef.current?.click()}
              className="flex items-center gap-1.5 text-[#2F4F4F] font-semibold rounded-xl transition-colors"
              style={{
                padding: "0.35rem 0.75rem", fontSize: "0.78rem",
                border: "1px solid rgba(152,193,142,0.5)",
                backgroundColor: "rgba(152,193,142,0.08)",
              }}
              onMouseOver={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(152,193,142,0.18)"; }}
              onMouseOut={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(152,193,142,0.08)"; }}
            >
              <Upload size={12} />
              Tải PDF
            </button>
          }
          topBadge={
            inputs.cvFile ? (
              <div
                className="flex items-center justify-between px-3 py-2 rounded-xl"
                style={{ backgroundColor: "rgba(152,193,142,0.1)", border: "1px solid rgba(152,193,142,0.3)" }}
              >
                <span className="flex items-center gap-1.5 text-xs font-semibold text-[#2F4F4F] truncate">
                  {isExtractingPDF.cv ? <Loader2 size={12} className="animate-spin" color="var(--primary)" /> : <CheckCircle size={12} color="var(--primary)" />}
                  {isExtractingPDF.cv ? "Đang đọc PDF..." : inputs.cvFile.name}
                </span>
                <button onClick={() => clearFile("cv")} className="text-[#5A6D6D] hover:text-[#B22222] transition-colors p-0.5 shrink-0" disabled={isExtractingPDF.cv}>
                  <X size={12} />
                </button>
              </div>
            ) : (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging("cv"); }}
                onDragLeave={() => setDragging(null)}
                onDrop={(e) => handleDrop(e, "cv")}
                onClick={() => cvFileInputRef.current?.click()}
                className="text-center cursor-pointer rounded-xl py-2 transition-all text-[#5A6D6D] text-xs"
                style={{
                  border: `1.5px dashed ${dragging === "cv" ? "var(--primary)" : "rgba(47,79,79,0.12)"}`,
                  backgroundColor: dragging === "cv" ? "rgba(152,193,142,0.06)" : "transparent",
                }}
              >
                <Upload size={13} color="var(--primary)" className="mx-auto mb-0.5" />
                Kéo thả PDF
              </div>
            )
          }
        >
          <input
            ref={cvFileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0], "cv")}
          />
          <textarea
            value={inputs.cvText}
            onChange={(e) => onChange({ cvText: e.target.value })}
            placeholder={"// Dán nội dung CV của bạn vào đây...\n\nHọ tên: Nguyễn Văn A\nKinh nghiệm: 3 năm tại...\nKỹ năng: React, TypeScript..."}
            className="flex-1 w-full min-h-[200px] resize-none outline-none bg-transparent text-[#2F4F4F] leading-relaxed text-sm"
            style={{ padding: "0.75rem 1rem", fontFamily: "'Inter', 'Courier New', monospace" }}
          />
        </TextCard>

        {/* LEFT: JD */}
        <TextCard
          title={<>Job Description (JD) <span className="text-gray-400 font-normal text-xs ml-1">(Tùy chọn)</span></>}
          subtitle="Dán text hoặc upload PDF"
          wordCountText={wordCount(inputs.jdText)}
          headerRight={
            <button
              onClick={() => jdFileInputRef.current?.click()}
              className="flex items-center gap-1.5 text-[#2F4F4F] font-semibold rounded-xl transition-colors"
              style={{
                padding: "0.35rem 0.75rem", fontSize: "0.78rem",
                border: "1px solid rgba(152,193,142,0.5)",
                backgroundColor: "rgba(152,193,142,0.08)",
              }}
              onMouseOver={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(152,193,142,0.18)"; }}
              onMouseOut={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(152,193,142,0.08)"; }}
            >
              <Upload size={12} />
              Tải PDF
            </button>
          }
          topBadge={
            inputs.jdFile ? (
              <div
                className="flex items-center justify-between px-3 py-2 rounded-xl"
                style={{ backgroundColor: "rgba(152,193,142,0.1)", border: "1px solid rgba(152,193,142,0.3)" }}
              >
                <span className="flex items-center gap-1.5 text-xs font-semibold text-[#2F4F4F] truncate">
                  {isExtractingPDF.jd ? <Loader2 size={12} className="animate-spin" color="var(--primary)" /> : <CheckCircle size={12} color="var(--primary)" />}
                  {isExtractingPDF.jd ? "Đang đọc PDF..." : inputs.jdFile.name}
                </span>
                <button onClick={() => clearFile("jd")} className="text-[#5A6D6D] hover:text-[#B22222] transition-colors p-0.5 shrink-0" disabled={isExtractingPDF.jd}>
                  <X size={12} />
                </button>
              </div>
            ) : (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging("jd"); }}
                onDragLeave={() => setDragging(null)}
                onDrop={(e) => handleDrop(e, "jd")}
                onClick={() => jdFileInputRef.current?.click()}
                className="text-center cursor-pointer rounded-xl py-2 transition-all text-[#5A6D6D] text-xs"
                style={{
                  border: `1.5px dashed ${dragging === "jd" ? "var(--primary)" : "rgba(47,79,79,0.12)"}`,
                  backgroundColor: dragging === "jd" ? "rgba(152,193,142,0.06)" : "transparent",
                }}
              >
                <Upload size={13} color="var(--primary)" className="mx-auto mb-0.5" />
                Kéo thả PDF
              </div>
            )
          }
        >
          <input
            ref={jdFileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0], "jd")}
          />
          <textarea
            value={inputs.jdText}
            onChange={(e) => onChange({ jdText: e.target.value })}
            placeholder={"// Dán yêu cầu công việc (JD) vào đây (Không bắt buộc)...\n\nVí dụ: Chúng tôi tìm kiếm một Kỹ sư Frontend..."}
            className="flex-1 w-full min-h-[200px] resize-none outline-none bg-transparent text-[#2F4F4F] leading-relaxed text-sm"
            style={{ padding: "1rem", fontFamily: "'Inter', 'Courier New', monospace" }}
            onFocus={(e) => {
              const card = e.target.closest<HTMLDivElement>(".bg-white");
              if (card) card.style.boxShadow = "0 0 0 2px var(--primary)";
            }}
            onBlur={(e) => {
              const card = e.target.closest<HTMLDivElement>(".bg-white");
              if (card) card.style.boxShadow = "";
            }}
          />
        </TextCard>
      </div>

      {/* ── Error + CTA — pinned at bottom, never scrolls away ── */}
      <div className="shrink-0 min-h-0 md:min-h-[140px] flex flex-col justify-end mt-2 md:mt-0">
        {(error || extractErrors.cv || extractErrors.jd) && (
          <div
            className="flex items-center gap-2.5 rounded-xl px-4 py-3 mb-3 text-sm font-medium text-[#B22222]"
            style={{ backgroundColor: "rgba(178,34,34,0.06)", border: "1px solid rgba(178,34,34,0.2)" }}
          >
            <AlertTriangle size={15} className="shrink-0" />
            {error || extractErrors.cv || extractErrors.jd}
          </div>
        )}

        <AnimatePresence mode="wait">
          {!isCvReady ? (
            <motion.div
              key="placeholder"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-[#2F4F4F]/[0.03] border border-dashed border-[#2F4F4F]/15 rounded-2xl p-4 md:p-6 text-center"
            >
              <div className="flex flex-row md:flex-col items-center justify-center gap-3 md:gap-2">
                <div className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-white flex items-center justify-center shadow-sm text-[#5A6D6D] shrink-0">
                  <FileText size={18} className="md:w-5 md:h-5" />
                </div>
                <div>
                  <p className="text-[#2F4F4F] font-semibold text-xs md:text-sm">Cung cấp CV để bắt đầu</p>
                  <p className="text-[#5A6D6D] text-[10px] md:text-xs">Bé Đậu cần nội dung CV của bạn.</p>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="actions"
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              className="flex flex-col gap-4"
            >
              <div className="flex items-center gap-2 px-1">
                <div className="w-1.5 h-4 bg-(--primary) rounded-full" />
                <h3 className="font-heading font-bold text-[#2F4F4F] text-sm">Chọn tính năng bạn muốn sử dụng:</h3>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-4 sm:mb-0">
                {/* Action Card 1: Analyze */}
                <button
                  onClick={handleAnalyzeClick}
                  disabled={isAnalyzing || isStartingInterview || isWriting}
                  className="flex flex-row md:flex-col items-center md:items-start gap-3 md:gap-2 p-3 md:p-4 rounded-2xl bg-white border-2 border-(--primary)/20 hover:border-(--primary) hover:bg-[#F9F9F2] transition-all text-left group shadow-sm disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <div className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-(--primary)/10 text-(--primary) flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                    {isAnalyzing ? <Loader2 className="animate-spin w-4 h-4 md:w-5 md:h-5" /> : <Sparkles className="w-4 h-4 md:w-5 md:h-5" />}
                  </div>
                  <div>
                    <h3 className="font-heading font-bold text-[#2F4F4F] text-sm mb-0.5 group-hover:text-(--primary) transition-colors">
                      {isAnalyzing ? "Đang xử lý..." : "Tối ưu CV"}
                    </h3>
                    <p className="text-[11px] text-[#5A6D6D] leading-tight">Phân tích CV chuẩn ATS.</p>
                  </div>
                </button>

                {/* Action Card 2: Interview */}
                <button
                  onClick={handleInterviewClick}
                  disabled={isAnalyzing || isStartingInterview || isWriting}
                  className="flex flex-row md:flex-col items-center md:items-start gap-3 md:gap-2 p-3 md:p-4 rounded-2xl bg-white border-2 border-orange-400/20 hover:border-orange-400 hover:bg-orange-50 transition-all text-left group shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <div className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-orange-400/10 text-orange-500 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                    {isStartingInterview ? <Loader2 className="animate-spin w-4 h-4 md:w-5 md:h-5" /> : <Mic className="w-4 h-4 md:w-5 md:h-5" />}
                  </div>
                  <div>
                    <h3 className="font-heading font-bold text-[#2F4F4F] text-sm mb-0.5 group-hover:text-orange-500 transition-colors">
                      {isStartingInterview ? "Đang xử lý..." : "Phỏng vấn 1-1"}
                    </h3>
                    <p className="text-[11px] text-[#5A6D6D] leading-tight">Luyện tập trả lời câu hỏi.</p>
                  </div>
                </button>

                {/* Action Card 3: Writing Assistant */}
                <button
                  onClick={handleWriteClick}
                  disabled={isAnalyzing || isStartingInterview || isWriting}
                  className="flex flex-row md:flex-col items-center md:items-start gap-3 md:gap-2 p-3 md:p-4 rounded-2xl bg-white border-2 border-purple-400/20 hover:border-purple-400 hover:bg-purple-50 transition-all text-left group shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <div className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-purple-400/10 text-purple-600 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                    {isWriting ? <Loader2 className="animate-spin w-4 h-4 md:w-5 md:h-5" /> : <PenTool className="w-4 h-4 md:w-5 md:h-5" />}
                  </div>
                  <div>
                    <h3 className="font-heading font-bold text-[#2F4F4F] text-sm mb-0.5 group-hover:text-purple-600 transition-colors">
                      {isWriting ? "Đang xử lý..." : "Trợ lý Viết"}
                    </h3>
                    <p className="text-[11px] text-[#5A6D6D] leading-tight">Email, LinkedIn, Zalo...</p>
                  </div>
                </button>

                {/* Action Card 4: Job Finder */}
                <button
                  onClick={onSearchJobs}
                  disabled={isAnalyzing || isStartingInterview || isWriting}
                  className="flex flex-row md:flex-col items-center md:items-start gap-3 md:gap-2 p-3 md:p-4 rounded-2xl bg-white border-2 border-blue-400/20 hover:border-blue-500 hover:bg-blue-50 transition-all text-left group shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <div className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-blue-500/10 text-blue-600 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                    <Briefcase className="w-4 h-4 md:w-5 md:h-5" />
                  </div>
                  <div>
                    <h3 className="font-heading font-bold text-[#2F4F4F] text-sm mb-0.5 group-hover:text-blue-600 transition-colors">
                      Tìm việc làm
                    </h3>
                    <p className="text-[11px] text-[#5A6D6D] leading-tight">Tìm việc phù hợp CV.</p>
                  </div>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
