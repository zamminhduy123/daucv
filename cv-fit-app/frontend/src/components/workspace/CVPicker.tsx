"use client";

import { CheckCircle2, FileText, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import type { UserCV } from "@/types";
import CVPdfThumb from "./CVPdfThumb";

export const MAX_CVS = 10;

interface CVPickerProps {
  cvs: UserCV[];
  selectedId: string | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onAdd: () => void;
}

function formatEditedAt(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (minutes < 1) return "Vừa xong";
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} ngày trước`;
  try {
    return new Date(iso).toLocaleDateString("vi-VN");
  } catch {
    return "";
  }
}

function previewLines(text: string): { heading: string; body: string[] } {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return { heading: lines[0] ?? "", body: lines.slice(1, 15) };
}

function CardPreview({ cv }: { cv: UserCV }) {
  const [thumbFailed, setThumbFailed] = useState(false);
  const [pdfFailed, setPdfFailed] = useState(false);
  // A freshly minted signed URL or thumbnail deserves a fresh attempt.
  useEffect(() => {
    queueMicrotask(() => {
      setPdfFailed(false);
      setThumbFailed(false);
    });
  }, [cv.pdf_url, cv.thumbnail_file_id]);

  const hasPdf = Boolean(cv.pdf_file_id || cv.thumbnail_file_id || cv.pdf_url);

  if (hasPdf && !thumbFailed) {
    return (
      <div className="relative aspect-[210/297] overflow-hidden bg-[#FDFDFB] pointer-events-none select-none">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/api/cv/${cv.id}/thumbnail${cv.thumbnail_file_id ? `?v=${encodeURIComponent(cv.thumbnail_file_id)}` : ""}`}
          alt={cv.cv_filename}
          className="h-full w-full object-cover object-top"
          loading="lazy"
          onError={() => setThumbFailed(true)}
        />
      </div>
    );
  }

  if (cv.pdf_url && !pdfFailed) {
    return <CVPdfThumb url={cv.pdf_url} label={cv.cv_filename} onError={() => setPdfFailed(true)} />;
  }
  const { heading, body } = previewLines(cv.cv_text);
  return (
    <div className="relative aspect-[210/297] overflow-hidden bg-[#FDFDFB] p-3 pointer-events-none select-none">
      {heading ? (
        <p className="text-center text-[11px] font-black text-[#2F4F4F] leading-tight line-clamp-2">{heading}</p>
      ) : (
        <p className="text-center text-[11px] font-black text-gray-300 leading-tight">
          <FileText size={14} className="inline" />
        </p>
      )}
      <div className="mt-1.5 space-y-1">
        {body.map((line, i) => (
          <p key={i} className="text-[8px] leading-snug text-gray-500 line-clamp-2">{line}</p>
        ))}
      </div>
      <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-white to-transparent" />
    </div>
  );
}

export default function CVPicker({ cvs, selectedId, isLoading, error, onRetry, onSelect, onDelete, onAdd }: CVPickerProps) {
  const atCap = cvs.length >= MAX_CVS;

  return (
    <div className="bg-white rounded-2xl border border-[#2F4F4F]/8 shadow-sm">
      <div className="px-4 py-3 border-b border-[#2F4F4F]/8 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-black text-[#2F4F4F]">CV của tôi</h2>
          <p className="text-[11px] text-[#5A6D6D]">Chọn CV để phân tích ({cvs.length}/{MAX_CVS}).</p>
        </div>
        <button
          type="button"
          onClick={onAdd}
          disabled={atCap}
          title={atCap ? `Tối đa ${MAX_CVS} CV — xóa bớt để thêm mới.` : "Tải CV mới"}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-xl bg-[#6A9B5E] px-4 py-2 text-xs font-bold text-white shadow-lg shadow-[#6A9B5E]/20 hover:bg-[#5a874e] active:scale-95 disabled:opacity-50 disabled:pointer-events-none"
        >
          <Plus size={14} />
          CV mới
        </button>
      </div>
      <div className="p-3">
        {error ? (
          <div className="rounded-2xl border border-[#B22222]/20 bg-[#B22222]/5 p-4 text-center">
            <p className="text-xs font-bold text-[#B22222]">Không tải được danh sách CV.</p>
            <p className="mt-1 text-[11px] text-[#B22222]/80">{error}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-[#6A9B5E] px-4 py-2 text-xs font-bold text-white shadow-lg shadow-[#6A9B5E]/20 hover:bg-[#5a874e] active:scale-95"
            >
              <RefreshCw size={13} />
              Thử lại
            </button>
          </div>
        ) : isLoading && cvs.length === 0 ? (
          <div className="flex items-center gap-2 px-3 py-4 text-xs text-gray-400">
            <Loader2 size={14} className="animate-spin" />
            Đang tải danh sách CV...
          </div>
        ) : cvs.length === 0 ? (
          <div className="rounded-2xl border-2 border-dashed border-[#2F4F4F]/10 bg-white/70 p-6 text-center">
            <p className="text-xs font-bold text-[#2F4F4F]">Bạn chưa có CV nào.</p>
            <p className="mt-1 text-[11px] text-[#5A6D6D]">Bấm “CV mới” ở trên để dán text hoặc tải PDF.</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
              {cvs.map((cv) => {
                const selected = cv.id === selectedId;
                return (
                  <div
                    key={cv.id}
                    onClick={() => onSelect(cv.id)}
                    className={`rounded-2xl border bg-white overflow-hidden cursor-pointer transition-all hover-elevate ${
                      selected
                        ? "border-[#6A9B5E] ring-2 ring-[#6A9B5E]/30 shadow-md"
                        : "border-[#2F4F4F]/8 shadow-sm hover:border-[#6A9B5E]/30"
                    }`}
                  >
                    {/* First-page preview (PDF thumbnail, text fallback) */}
                    <div className="relative">
                      <div className="pointer-events-none">
                        <CardPreview cv={cv} />
                      </div>
                      {selected && (
                        <span className="absolute top-2 right-2 rounded-full bg-[#6A9B5E] p-0.5">
                          <CheckCircle2 size={14} className="text-white" />
                        </span>
                      )}
                    </div>
                    {/* Caption bar */}
                    <div className="flex items-center gap-2 border-t border-[#2F4F4F]/8 px-3 py-2.5">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-black text-[#2F4F4F]">{cv.cv_filename}</p>
                        <p className="text-[11px] text-gray-400">Đã sửa {formatEditedAt(cv.created_at)}</p>
                      </div>
                      <button
                        type="button"
                        aria-label={`Xóa ${cv.cv_filename}`}
                        className="rounded-lg p-1.5 text-gray-400 hover:text-[#B22222] hover:bg-[#B22222]/5 shrink-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!confirm("Xóa CV này? Các bản CV đã tối ưu không bị ảnh hưởng.")) return;
                          onDelete(cv.id);
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
            {atCap && (
              <p className="mt-3 text-center text-[11px] text-[#5A6D6D]">
                Đã đạt tối đa {MAX_CVS} CV — xóa một CV cũ để thêm CV mới.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
