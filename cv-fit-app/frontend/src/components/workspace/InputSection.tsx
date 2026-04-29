"use client";

import { useRef, useState } from "react";
import { Upload, FileText, X, CheckCircle, AlertTriangle, Sparkles, Mic, Loader2 } from "lucide-react";
import type { WorkspaceInputs } from "@/types";
import { wordCount } from "@/lib/utils";
import { extractPdfAPI } from "@/lib/api";

interface InputSectionProps {
  inputs: WorkspaceInputs;
  onChange: (patch: Partial<WorkspaceInputs>) => void;
  onAnalyze: () => void;
  onInterview: () => void;
  isAnalyzing: boolean;
  isStartingInterview: boolean;
  error: string;
}

// ── Sub-component: textarea card shell ────────────────────────────────────────
interface TextCardProps {
  title: string;
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
export default function InputSection({ inputs, onChange, onAnalyze, onInterview, isAnalyzing, isStartingInterview, error }: InputSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [isExtractingPDF, setIsExtractingPDF] = useState(false);
  const [extractError, setExtractError] = useState("");

  const handleFile = async (file: File) => {
    if (file.type !== "application/pdf") {
      onChange({ cvFile: null, cvText: "" });
      setExtractError("Vui lòng tải lên file PDF.");
      return;
    }
    
    onChange({ cvFile: file });
    setExtractError("");
    setIsExtractingPDF(true);

    try {
      const result = await extractPdfAPI(file);
      if (result.error) {
        setExtractError(result.error);
        onChange({ cvFile: null, cvText: `[Lỗi trích xuất: ${result.error}]` });
      } else {
        onChange({ cvText: result.text || "" });
      }
    } catch (err: any) {
      setExtractError(err.message || "Lỗi kết nối");
    } finally {
      setIsExtractingPDF(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const clearFile = () => onChange({ cvFile: null, cvText: "" });

  return (
    // Full-height flex column — fills whatever height the parent gives it
    <div className="flex flex-col gap-4 h-[calc(100vh-100px)] ">

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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">

        {/* LEFT: JD */}
        <TextCard
          title="Job Description (JD)"
          subtitle="Yêu cầu từ nhà tuyển dụng"
          wordCountText={wordCount(inputs.jdText)}
        >
          <textarea
            value={inputs.jdText}
            onChange={(e) => onChange({ jdText: e.target.value })}
            placeholder={"// Dán yêu cầu công việc (JD) vào đây...\n\nVí dụ: Chúng tôi tìm kiếm một Kỹ sư Frontend..."}
            className="flex-1 w-full resize-none outline-none bg-transparent text-[#2F4F4F] leading-relaxed text-sm"
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

        {/* RIGHT: CV */}
        <TextCard
          title="CV của bạn"
          subtitle="Dán text hoặc upload PDF"
          wordCountText={wordCount(inputs.cvText)}
          headerRight={
            <button
              onClick={() => fileInputRef.current?.click()}
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
                  {isExtractingPDF ? <Loader2 size={12} className="animate-spin" color="var(--primary)" /> : <CheckCircle size={12} color="var(--primary)" />}
                  {isExtractingPDF ? "Đang đọc PDF..." : inputs.cvFile.name}
                </span>
                <button onClick={clearFile} className="text-[#5A6D6D] hover:text-[#B22222] transition-colors p-0.5 shrink-0" disabled={isExtractingPDF}>
                  <X size={12} />
                </button>
              </div>
            ) : (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="text-center cursor-pointer rounded-xl py-2 transition-all text-[#5A6D6D] text-xs"
                style={{
                  border: `1.5px dashed ${dragging ? "var(--primary)" : "rgba(47,79,79,0.12)"}`,
                  backgroundColor: dragging ? "rgba(152,193,142,0.06)" : "transparent",
                }}
              >
                <Upload size={13} color="var(--primary)" className="mx-auto mb-0.5" />
                Kéo thả PDF
              </div>
            )
          }
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <textarea
            value={inputs.cvText}
            onChange={(e) => onChange({ cvText: e.target.value })}
            placeholder={"// Dán nội dung CV của bạn vào đây...\n\nHọ tên: Nguyễn Văn A\nKinh nghiệm: 3 năm tại...\nKỹ năng: React, TypeScript..."}
            className="flex-1 w-full resize-none outline-none bg-transparent text-[#2F4F4F] leading-relaxed text-sm"
            style={{ padding: "0.75rem 1rem", fontFamily: "'Inter', 'Courier New', monospace" }}
          />
        </TextCard>
      </div>

      {/* ── Error + CTA — pinned at bottom, never scrolls away ── */}
      <div className="shrink-0">
        {(error || extractError) && (
          <div
            className="flex items-center gap-2.5 rounded-xl px-4 py-3 mb-3 text-sm font-medium text-[#B22222]"
            style={{ backgroundColor: "rgba(178,34,34,0.06)", border: "1px solid rgba(178,34,34,0.2)" }}
          >
            <AlertTriangle size={15} className="shrink-0" />
            {error || extractError}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 mt-2">
          {/* Action Card 1: Analyze */}
          <button
            onClick={onAnalyze}
            disabled={isAnalyzing || isStartingInterview}
            className="flex items-start gap-3 md:gap-4 p-3 md:p-4 rounded-2xl bg-white border-2 border-(--primary)/20 hover:border-(--primary) hover:bg-[#F9F9F2] transition-all text-left group shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-(--primary)/10 text-(--primary) flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
              {isAnalyzing ? <Loader2 className="animate-spin w-5 h-5 md:w-6 md:h-6" /> : <Sparkles className="w-5 h-5 md:w-6 md:h-6" />}
            </div>
            <div>
              <h3 className="font-heading font-bold text-[#2F4F4F] text-base md:text-lg mb-0.5 md:mb-1 group-hover:text-(--primary) transition-colors">
                {isAnalyzing ? "Đang xử lý..." : "Chăm chút & Tối ưu CV"}
              </h3>
              <p className="text-xs md:text-sm text-[#5A6D6D]">AI phân tích và gợi ý sửa CV chuẩn ATS.</p>
            </div>
          </button>

          {/* Action Card 2: Interview */}
          <button
            onClick={onInterview}
            disabled={isAnalyzing || isStartingInterview}
            className="flex items-start gap-3 md:gap-4 p-3 md:p-4 rounded-2xl bg-white border-2 border-orange-400/20 hover:border-orange-400 hover:bg-orange-50 transition-all text-left group shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-orange-400/10 text-orange-500 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
              {isStartingInterview ? <Loader2 className="animate-spin w-5 h-5 md:w-6 md:h-6" /> : <Mic className="w-5 h-5 md:w-6 md:h-6" />}
            </div>
            <div>
              <h3 className="font-heading font-bold text-[#2F4F4F] text-base md:text-lg mb-0.5 md:mb-1 group-hover:text-orange-500 transition-colors">
                {isStartingInterview ? "Đang xử lý..." : "Phỏng vấn 1-1 với Bé Đậu"}
              </h3>
              <p className="text-xs md:text-sm text-[#5A6D6D]">Luyện tập trả lời câu hỏi dựa trên CV và JD.</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
