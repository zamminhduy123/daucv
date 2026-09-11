"use client";

import { useRef, useState } from "react";
import { FileText, Loader2, Upload, X } from "lucide-react";
import { extractPdfAPI, type PdfExtractResult } from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";

interface UploadCVModalProps {
  open: boolean;
  defaultName: string;
  /** true when the user already has >=1 CV (extra slot costs 1 credit) */
  isExtraSlot: boolean;
  credits: number | null;
  isUploading: boolean;
  uploadError: string | null;
  onClose: () => void;
  onUpload: (args: {
    file: File;
    name: string;
    text: string;
    rawExtractionRef: PdfExtractResult["raw_extraction_ref"];
    pdfFileId: string | null;
    thumbnailFileId: string | null;
  }) => void;
}

const MAX_PDF_BYTES = 10 * 1024 * 1024;

function baseNameOf(filename: string): string {
  return filename.replace(/\.pdf$/i, "").trim();
}

export default function UploadCVModal({
  open,
  defaultName,
  isExtraSlot,
  credits,
  isUploading,
  uploadError,
  onClose,
  onUpload,
}: UploadCVModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState(defaultName);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset-on-open without an effect (render-time adjustment keeps hook
  // order stable and avoids cascading renders when `open` flips).
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) {
      setName(defaultName);
      setFile(null);
      setError(null);
      setIsExtracting(false);
    }
  }

  // Mirror an incoming async upload error into local error state without
  // an effect (render-time adjustment; the effect version cascades).
  const [prevUploadError, setPrevUploadError] = useState(uploadError);
  if (uploadError !== prevUploadError) {
    setPrevUploadError(uploadError);
    if (uploadError) setError(uploadError);
  }

  if (!open) return null;

  const outOfCredits = isExtraSlot && (credits ?? 0) < 1;
  const nameValid = name.trim().length > 0;
  const busy = isExtracting || isUploading;

  const pickFile = (candidate: File | undefined | null) => {
    if (!candidate) return;
    if (candidate.type !== "application/pdf" && !candidate.name.toLowerCase().endsWith(".pdf")) {
      setError("Vui lòng tải lên file PDF.");
      return;
    }
    if (candidate.size > MAX_PDF_BYTES) {
      setError("File quá lớn. Giới hạn 10 MB.");
      return;
    }
    setError(null);
    setFile(candidate);
    if (!name.trim()) setName(baseNameOf(candidate.name));
  };

  const handleUpload = async () => {
    if (!file || !nameValid || busy || outOfCredits) return;
    setIsExtracting(true);
    setError(null);
    try {
      const result = (await extractPdfAPI(file, "cv", undefined)) as PdfExtractResult;
      if (result.error || !result.text?.trim()) {
        throw new Error("Không đọc được nội dung PDF. Hãy thử file khác.");
      }
      if (!result.raw_extraction_ref) {
        throw new Error("Thiếu dữ liệu layout từ file PDF.");
      }
      onUpload({
        file,
        name: name.trim(),
        text: result.text,
        rawExtractionRef: result.raw_extraction_ref,
        pdfFileId: result.file_info?.id ?? null,
        thumbnailFileId: result.thumbnail_file_id ?? null,
      });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setIsExtracting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Tải CV mới"
    >
      <button
        type="button"
        aria-label="Đóng"
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/50 cursor-pointer"
      />
      <div className="relative w-full max-w-[520px] rounded-2xl bg-white shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-bold text-slate-900">Tải CV mới</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-slate-700"
            aria-label="Đóng"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          <div>
            <label htmlFor="cv-name" className="text-xs font-bold tracking-wide text-slate-700">
              TÊN CV *
            </label>
            <input
              id="cv-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="VD: Nguyen Van A - Backend"
              className="mt-1.5 w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:outline-none focus:ring-2 focus:ring-[#2D7A58]/10"
            />
          </div>

          <div>
            <p className="text-xs font-bold tracking-wide text-slate-700">FILE PDF *</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                pickFile(e.dataTransfer.files?.[0]);
              }}
              className={`mt-1.5 flex w-full items-center gap-3 rounded-xl border-2 border-dashed px-4 py-4 text-left transition-colors cursor-pointer ${
                dragging ? "border-[#2D7A58] bg-[#EAF5EC]/40" : "border-gray-200 hover:border-[#2D7A58]/50"
              }`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-500">
                <FileText size={20} />
              </span>
              {file ? (
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-slate-800">{file.name}</span>
                  <span className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                </span>
              ) : (
                <span className="flex-1 text-sm text-gray-400">Kéo thả hoặc bấm để chọn file PDF (tối đa 10MB)</span>
              )}
              <Upload size={16} className="shrink-0 text-gray-400" />
            </button>
          </div>

          {/* PLACEHOLDER: swap src with the real good-example CV image when ready. */}
          <div className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50/60 p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/good-cv-example.png"
              alt="Mẫu CV 1 cột chuẩn"
              className="h-24 w-auto shrink-0 rounded-md border border-gray-200 bg-white object-cover object-top"
            />
            <p className="text-xs leading-relaxed text-slate-600">
              <span className="font-bold text-slate-800">Mẫu CV chuẩn:</span> file PDF{" "}
              <span className="font-semibold">1 cột, chữ rõ</span> cho kết quả tốt nhất.
              CV 2 cột, bảng biểu hoặc file scan có thể bị thiếu sót khi trích xuất.
            </p>
          </div>

          {isExtraSlot && (
            <p className="rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
              {outOfCredits
                ? "Hết credit — cần 1 credit để mở khóa CV mới. Hãy nạp thêm."
                : "CV thứ 2 sẽ tốn 1 credit để upload."}
            </p>
          )}

          {error && (
            <p role="alert" className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
              {error}
            </p>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-100 bg-gray-50/60">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-gray-50 cursor-pointer"
          >
            HỦY
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || !nameValid || busy || outOfCredits}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#2D7A58] px-5 py-2 text-xs font-bold text-white hover:bg-[#246347] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {(isExtracting || isUploading) && <Loader2 size={13} className="animate-spin" />}
            {isExtracting ? "ĐANG ĐỌC PDF..." : isExtraSlot ? "MỞ KHÓA & TẢI LÊN — 1 CREDIT" : "TẢI LÊN & CHỈNH SỬA"}
          </button>
        </div>
      </div>
    </div>
  );
}
