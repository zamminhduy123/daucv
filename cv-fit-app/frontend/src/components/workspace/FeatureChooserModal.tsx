"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, BarChart3, FileText, Loader2, MessagesSquare, Search, Sparkles, Upload, X } from "lucide-react";
import { extractPdfAPI } from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";

export type FeatureKind = "analyze" | "tailor" | "interview" | "jobs";

interface FeatureChooserModalProps {
  open: boolean;
  cvName: string;
  /** false when the CV has never been validly saved */
  canUseFeatures: boolean;
  initialJdText?: string;
  onClose: () => void;
  onPick: (kind: FeatureKind, jdText?: string, jdFileName?: string | null) => void;
}

const FEATURES: {
  kind: FeatureKind;
  icon: typeof Sparkles;
  title: string;
  desc: string;
  tile: string;
  badge: string;
}[] = [
  { kind: "analyze", icon: BarChart3, title: "Phân tích CV", desc: "Chấm điểm & nhận xét, không cần JD.", tile: "hover:border-emerald-600/50 hover:bg-emerald-50/40", badge: "bg-emerald-100 text-emerald-700" },
  { kind: "tailor", icon: Sparkles, title: "Tối ưu theo JD", desc: "Bắt buộc tải file JD để tailor.", tile: "hover:border-blue-600/50 hover:bg-blue-50/40", badge: "bg-blue-100 text-blue-700" },
  { kind: "interview", icon: MessagesSquare, title: "Phỏng vấn thử", desc: "Luyện trả lời từ CV đã lưu.", tile: "hover:border-rose-600/50 hover:bg-rose-50/40", badge: "bg-rose-100 text-rose-700" },
  { kind: "jobs", icon: Search, title: "Tìm việc", desc: "Gợi ý việc phù hợp từ CV.", tile: "hover:border-violet-600/50 hover:bg-violet-50/40", badge: "bg-violet-100 text-violet-700" },
];

export default function FeatureChooserModal({ open, cvName, canUseFeatures, initialJdText = "", onClose, onPick }: FeatureChooserModalProps) {
  const [step, setStep] = useState<"menu" | "jd">("menu");
  const [jdText, setJdText] = useState(initialJdText);
  const [jdFileName, setJdFileName] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [jdError, setJdError] = useState<string | null>(null);
  const jdFileInputRef = useRef<HTMLInputElement>(null);

  const close = () => {
    setStep("menu");
    setJdError(null);
    onClose();
  };

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  if (!open) return null;

  const pickJdFile = async (candidate: File | undefined | null) => {
    if (!candidate) return;
    if (candidate.type !== "application/pdf" && !candidate.name.toLowerCase().endsWith(".pdf")) {
      setJdError("JD: vui lòng tải lên file PDF.");
      return;
    }
    if (candidate.size > 10 * 1024 * 1024) {
      setJdError("JD: file quá lớn. Giới hạn 10 MB.");
      return;
    }
    setIsExtracting(true);
    setJdError(null);
    try {
      const result = await extractPdfAPI(candidate, "jd", undefined);
      if (result.error || !result.text?.trim()) {
        throw new Error("Không đọc được nội dung PDF. Hãy dán text JD trực tiếp.");
      }
      setJdText(result.text.trim());
      setJdFileName(candidate.name);
    } catch (err) {
      setJdError(apiErrorMessage(err));
    } finally {
      setIsExtracting(false);
    }
  };

  // JD step for "Tối ưu theo JD" — a PDF upload is mandatory; the
  // textarea only previews/corrects the extracted text.
  if (step === "jd") {
    const jdValid = jdText.trim().length > 20;
    const jdUploaded = jdFileName !== null;
    const canContinue = jdValid && jdUploaded && !isExtracting;
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Nhập Job Description">
        <button type="button" aria-label="Đóng" onClick={close} className="absolute inset-0 bg-slate-900/50 cursor-pointer" />
        <div className="relative w-full max-w-[560px] rounded-2xl bg-white shadow-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
            <button type="button" onClick={() => setStep("menu")} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-slate-700" aria-label="Quay lại">
              <ArrowLeft size={16} />
            </button>
            <div className="min-w-0">
              <h2 className="text-base font-bold text-blue-700">Tối ưu theo JD</h2>
              <p className="truncate text-xs text-gray-500">{cvName} — dán hoặc tải JD để tailor</p>
            </div>
            <button type="button" onClick={close} className="ml-auto rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-slate-700" aria-label="Đóng">
              <X size={18} />
            </button>
          </div>
          <div className="space-y-3 p-6">
            <input
              ref={jdFileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => void pickJdFile(e.target.files?.[0])}
            />
            <button
              type="button"
              onClick={() => jdFileInputRef.current?.click()}
              disabled={isExtracting}
              className="flex w-full items-center gap-2 rounded-xl border-2 border-dashed border-blue-200 px-4 py-3 text-left text-sm text-gray-500 hover:border-blue-400 cursor-pointer disabled:opacity-50"
            >
              {isExtracting ? <Loader2 size={16} className="animate-spin text-blue-600" /> : <Upload size={16} className="text-blue-500" />}
              {jdFileName ? <span className="truncate font-semibold text-slate-700">{jdFileName}</span> : "Tải file PDF JD"}
              <FileText size={14} className="ml-auto shrink-0 text-gray-300" />
            </button>
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              onBlur={() => setJdText((v) => v.trim())}
              placeholder={jdUploaded ? "Nội dung JD từ file — sửa lại nếu trích xuất thiếu..." : "Tải file PDF JD ở trên để lấy nội dung..."}
              rows={8}
              className="w-full resize-y rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/10"
            />
            {!jdUploaded && !jdError && (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
                Bắt buộc: tải file PDF JD để tiếp tục tailor.
              </p>
            )}
            {jdUploaded && !jdValid && !jdError && (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
                File JD trích xuất quá ngắn — bổ sung nội dung vào ô trên (tối thiểu ~20 ký tự).
              </p>
            )}
            {jdError && (
              <p role="alert" className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                {jdError}
              </p>
            )}
          </div>
          <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-100 bg-gray-50/60">
            <button
              type="button"
              onClick={() => setStep("menu")}
              className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-gray-50 cursor-pointer"
            >
              QUAY LẠI
            </button>
            <button
              type="button"
              onClick={() => onPick("tailor", jdText.trim(), jdFileName)}
              disabled={!canContinue}
              className="rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              TIẾP TỤC TAILOR
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Chọn tính năng">
      <button type="button" aria-label="Đóng" onClick={onClose} className="absolute inset-0 bg-slate-900/50 cursor-pointer" />
      <div className="relative w-full max-w-[560px] rounded-2xl bg-white shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="min-w-0">
            <h2 className="text-base font-bold text-slate-900">CV đã sẵn sàng 🎉</h2>
            <p className="truncate text-xs text-gray-500">{cvName} — chọn tính năng tiếp theo</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-slate-700" aria-label="Đóng">
            <X size={18} />
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-6">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <button
                key={f.kind}
                type="button"
                disabled={!canUseFeatures}
                onClick={() => {
                  if (f.kind === "tailor") {
                    setJdText(initialJdText);
                    setJdFileName(null);
                    setJdError(null);
                    setStep("jd");
                  } else {
                    onPick(f.kind);
                  }
                }}
                className={`rounded-2xl border border-gray-200 p-4 text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${f.tile}`}
              >
                <span className={`inline-flex h-9 w-9 items-center justify-center rounded-xl ${f.badge}`}>
                  <Icon size={18} />
                </span>
                <span className="mt-2 block text-sm font-bold text-slate-800">{f.title}</span>
                <span className="text-xs text-gray-500">{f.desc}</span>
              </button>
            );
          })}
        </div>
        {!canUseFeatures && (
          <p className="px-6 pb-5 text-xs text-amber-700">Hãy lưu CV hợp lệ trước khi dùng tính năng.</p>
        )}
      </div>
    </div>
  );
}
