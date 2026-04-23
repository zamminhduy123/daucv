"use client";

import { useRef, useState } from "react";
import { Upload, FileText, X, CheckCircle, AlertTriangle, Sparkles, ChevronRight } from "lucide-react";
import type { WorkspaceInputs } from "@/types";
import { wordCount } from "@/lib/utils";

interface InputSectionProps {
  inputs: WorkspaceInputs;
  onChange: (patch: Partial<WorkspaceInputs>) => void;
  onAnalyze: () => void;
  loading: boolean;
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
    <div className="bg-white rounded-2xl border border-[#2F4F4F]/[0.08] shadow-sm flex flex-col overflow-hidden h-full">
      {/* Header — compact */}
      <div className="px-4 py-3 border-b border-[#2F4F4F]/[0.07] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: "rgba(152,193,142,0.15)" }}>
            <FileText size={15} color="#98C18E" />
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
      <div className="px-4 py-1.5 border-t border-[#2F4F4F]/[0.06] bg-[#FAFAFA] shrink-0">
        <span className="text-[10px] text-[#5A6D6D]">{wordCountText}</span>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function InputSection({ inputs, onChange, onAnalyze, loading, error }: InputSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = (file: File) => {
    if (file.type !== "application/pdf") {
      onChange({ cvFile: null, cvText: "" });
      return;
    }
    onChange({ cvFile: file, cvText: `[PDF đã tải lên: ${file.name}]` });
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
          <span className="text-[#98C18E] font-semibold">Bé Đậu sẽ lo phần còn lại.</span>
        </p>
      </div>

      {/* ── 2-col card grid — grows to fill space ── */}
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">

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
              if (card) card.style.boxShadow = "0 0 0 2px #98C18E";
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
                  <CheckCircle size={12} color="#98C18E" />
                  {inputs.cvFile.name}
                </span>
                <button onClick={clearFile} className="text-[#5A6D6D] hover:text-[#B22222] transition-colors p-0.5 shrink-0">
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
                  border: `1.5px dashed ${dragging ? "#98C18E" : "rgba(47,79,79,0.12)"}`,
                  backgroundColor: dragging ? "rgba(152,193,142,0.06)" : "transparent",
                }}
              >
                <Upload size={13} color="#98C18E" className="mx-auto mb-0.5" />
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
        {error && (
          <div
            className="flex items-center gap-2.5 rounded-xl px-4 py-3 mb-3 text-sm font-medium text-[#B22222]"
            style={{ backgroundColor: "rgba(178,34,34,0.06)", border: "1px solid rgba(178,34,34,0.2)" }}
          >
            <AlertTriangle size={15} className="shrink-0" />
            {error}
          </div>
        )}

        <div className="flex items-center justify-between">
          <p className="text-xs text-[#5A6D6D]">
            Phân tích xong trong ~2 giây
          </p>
          <button
            onClick={onAnalyze}
            disabled={loading}
            className="inline-flex items-center gap-2 font-heading font-bold text-white rounded-xl transition-all disabled:opacity-70 disabled:cursor-not-allowed"
            style={{
              padding: "0.75rem 2rem", fontSize: "1rem",
              backgroundColor: "#98C18E",
              boxShadow: "0 6px 20px rgba(152,193,142,0.35)",
            }}
            onMouseOver={(e) => {
              if (!loading) {
                (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-1px)";
                (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 10px 28px rgba(152,193,142,0.45)";
              }
            }}
            onMouseOut={(e) => {
              (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 20px rgba(152,193,142,0.35)";
            }}
          >
            <Sparkles size={18} />
            Chăm chút CV ✨
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
