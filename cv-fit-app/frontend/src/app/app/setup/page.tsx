"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Loader2, Pencil, Plus, Sparkles, Trash2, X } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useAuth } from "@/context/AuthContext";
import { connectivityMessage } from "@/lib/errorMessages";
import { prefillCVAPI, type PdfExtractResult } from "@/lib/api";
import { setCachedStructuredDoc } from "@/lib/document-cache";
import UploadCVModal from "@/components/workspace/UploadCVModal";
import CVPdfThumb from "@/components/workspace/CVPdfThumb";
import type { RawExtractionReference } from "@/types";

export default function SetupPage() {
  const router = useRouter();
  const {
    cvList,
    isCvListLoading,
    cvListError,
    refreshCvList,
    selectCV,
    uploadFileCV,
    deleteCV,
    updateWorkspace,
  } = useWorkspace();
  const { credits, refreshCredits, userId } = useAuth();

  const [modalOpen, setModalOpen] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [autoOpened, setAutoOpened] = useState(false);

  useEffect(() => {
    void refreshCvList();
    void refreshCredits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // First run: zero CVs → auto-open the upload modal (no dead end).
  useEffect(() => {
    if (!autoOpened && !isCvListLoading && !cvListError && cvList.length === 0) {
      queueMicrotask(() => {
        setAutoOpened(true);
        setModalOpen(true);
      });
    }
  }, [autoOpened, isCvListLoading, cvListError, cvList.length]);

  const actionCv = useMemo(() => cvList.find((cv) => cv.id === actionId) ?? null, [cvList, actionId]);
  const isExtraSlot = cvList.length >= 1;

  const handleUpload = async (args: {
    file: File;
    name: string;
    text: string;
    rawExtractionRef: PdfExtractResult["raw_extraction_ref"];
    pdfFileId: string | null;
  }) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const rawRef: RawExtractionReference | null = args.rawExtractionRef
        ? {
            id: args.rawExtractionRef.id,
            extraction_version: args.rawExtractionRef.extraction_version ?? "2.0",
            method: (args.rawExtractionRef.method as RawExtractionReference["method"]) ?? "native_blocks",
          }
        : null;
      const row = await uploadFileCV(args.text, args.name, rawRef, args.pdfFileId);
      if (row?.id) {
        try {
          const prefill = await prefillCVAPI(args.text, rawRef?.id, row.id);
          setCachedStructuredDoc(row.id, prefill.prefill_document_v2, userId);
        } catch (prefillErr) {
          console.warn("Pre-warm prefill failed; review page will fallback gracefully:", prefillErr);
        }
      }
      await refreshCredits(true);
      setModalOpen(false);
      router.push("/app/review");
    } catch (err) {
      setUploadError(connectivityMessage(err));
    } finally {
      setIsUploading(false);
    }
  };

  const openReview = (id: string, options?: { features?: boolean }) => {
    const row = cvList.find((cv) => cv.id === id);
    selectCV(id);
    if (row) {
      updateWorkspace({ cvText: row.cv_text, cvFileName: row.cv_filename });
    }
    setActionId(null);
    router.push(options?.features ? "/app/review?features=1" : "/app/review");
  };

  const handleDeleteCV = async (id: string, filename: string) => {
    if (!window.confirm(`Xóa "${filename}"? Các bản CV đã tối ưu không bị ảnh hưởng.`)) return;
    await deleteCV(id);
  };

  return (
    <div className="h-full overflow-y-auto px-4">
      <div className="mx-auto">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-slate-900">CV của tôi</h1>
            <p className="text-xs text-gray-500">Tải CV PDF, chỉnh sửa cho chính xác, rồi chọn tính năng.</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setUploadError(null);
              setModalOpen(true);
            }}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#2D7A58] px-4 py-2 text-xs font-bold text-white hover:bg-[#246347] cursor-pointer"
          >
            <Plus size={14} />
            CV mới
          </button>
        </div>

        {cvListError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-xs font-bold text-red-700">Không tải được danh sách CV.</p>
            <p className="mt-1 text-[11px] text-red-600">{cvListError}</p>
            <button
              type="button"
              onClick={() => void refreshCvList()}
              className="mt-3 rounded-xl bg-[#2D7A58] px-4 py-2 text-xs font-bold text-white cursor-pointer"
            >
              Thử lại
            </button>
          </div>
        ) : isCvListLoading && cvList.length === 0 ? (
          <div className="mt-8 flex items-center justify-center gap-2 text-xs text-gray-400">
            <Loader2 size={14} className="animate-spin" />
            Đang tải danh sách CV...
          </div>
        ) : cvList.length === 0 ? (
          <div className="mt-8 rounded-2xl border-2 border-dashed border-gray-200 p-8 text-center">
            <p className="text-sm font-bold text-slate-700">Bạn chưa có CV nào.</p>
            <p className="mt-1 text-xs text-gray-500">Bấm “CV mới” để tải file PDF đầu tiên.</p>
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {cvList.map((cv) => (
              <CvCard
                key={cv.id}
                id={cv.id}
                filename={cv.cv_filename}
                pdfUrl={cv.pdf_url ?? null}
                text={cv.cv_text}
                createdAt={cv.created_at}
                onOpen={() => setActionId(cv.id)}
                onDelete={() => void handleDeleteCV(cv.id, cv.cv_filename)}
              />
            ))}
          </div>
        )}
      </div>

      <UploadCVModal
        open={modalOpen}
        defaultName=""
        isExtraSlot={isExtraSlot}
        credits={credits}
        isUploading={isUploading}
        uploadError={uploadError}
        onClose={() => {
          if (!isUploading) setModalOpen(false);
        }}
        onUpload={(args) => void handleUpload(args)}
      />

      {actionCv && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={actionCv.cv_filename}>
          <button type="button" aria-label="Đóng" onClick={() => setActionId(null)} className="absolute inset-0 bg-slate-900/50 cursor-pointer" />
          <div className="relative w-full max-w-sm rounded-2xl bg-white p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-900">{actionCv.cv_filename}</p>
                <p className="text-xs text-gray-500">Chọn thao tác tiếp theo</p>
              </div>
              <button type="button" onClick={() => setActionId(null)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100" aria-label="Đóng">
                <X size={16} />
              </button>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => openReview(actionCv.id)}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-gray-200 px-3 py-2.5 text-xs font-bold text-slate-700 hover:bg-gray-50 cursor-pointer"
              >
                <Pencil size={14} />
                Chỉnh sửa
              </button>
              <button
                type="button"
                onClick={() => openReview(actionCv.id, { features: true })}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-[#2D7A58] px-3 py-2.5 text-xs font-bold text-white hover:bg-[#246347] cursor-pointer"
              >
                <Sparkles size={14} />
                Dùng tính năng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatRelativeTime(createdAt: string): string {
  try {
    const t = new Date(createdAt).getTime();
    if (Number.isNaN(t)) return "";
    const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
    return mins < 1 ? "Vừa xong" : mins < 60 ? `${mins} phút trước` : `${Math.round(mins / 60)} giờ trước`;
  } catch {
    return "";
  }
}

function CvCard({
  filename,
  pdfUrl,
  text,
  createdAt,
  onOpen,
  onDelete,
}: {
  id: string;
  filename: string;
  pdfUrl: string | null;
  text: string;
  createdAt: string;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const [pdfFailed, setPdfFailed] = useState(false);
  const [edited, setEdited] = useState("");

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      setEdited(formatRelativeTime(createdAt));
    });
    return () => cancelAnimationFrame(id);
  }, [createdAt]);

  const firstLine = text.split("\n").map((l) => l.trim()).filter(Boolean)[0] ?? "";
  return (
    <div onClick={onOpen} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm cursor-pointer hover:border-[#2D7A58]/40 transition-colors">
      <div className="aspect-1/1.25 overflow-hidden bg-[#F7F9F7] pointer-events-none">
        {pdfUrl && !pdfFailed ? (
          <CVPdfThumb url={pdfUrl} label={filename} onError={() => setPdfFailed(true)} />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-1 p-3 text-center">
            <FileText size={20} className="text-gray-300" />
            <p className="line-clamp-2 text-[11px] font-semibold text-gray-500">{firstLine || filename}</p>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 border-t border-gray-100 px-3 py-2.5">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-slate-800">{filename}</p>
          {edited && <p className="text-[11px] text-gray-400">Đã sửa {edited}</p>}
        </div>
        <button
          type="button"
          aria-label={`Xóa ${filename}`}
          className="rounded-lg p-1.5 text-gray-400 hover:text-[#B22222] hover:bg-red-50 shrink-0 cursor-pointer"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
}
