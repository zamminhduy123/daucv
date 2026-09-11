"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Loader2, Pencil, Plus, Sparkles, Trash2, X, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { toast } from "sonner";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useAuth } from "@/context/AuthContext";
import { connectivityMessage } from "@/lib/errorMessages";
import { prefillCVAPI, type PdfExtractResult } from "@/lib/api";
import { setCachedStructuredDoc } from "@/lib/document-cache";
import UploadCVModal from "@/components/workspace/UploadCVModal";
import type { RawExtractionReference } from "@/types";

const gridVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.05, duration: 0.2 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 14, scale: 0.98 },
  visible: (index: number = 0) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { delay: 0.05 + index * 0.05, duration: 0.35, ease: [0.25, 0.1, 0.25, 1] as const },
  }),
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.18 } },
};

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
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; filename: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [autoOpened, setAutoOpened] = useState(false);
  const reduceMotion = useReducedMotion();

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
    thumbnailFileId: string | null;
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
      const row = await uploadFileCV(args.text, args.name, rawRef, args.pdfFileId, args.thumbnailFileId);
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

  const handleDeleteCV = (id: string, filename: string) => {
    setConfirmDelete({ id, filename });
  };

  const executeDeleteCV = async () => {
    if (!confirmDelete || isDeleting) return;
    setIsDeleting(true);
    const target = confirmDelete;
    try {
      await deleteCV(target.id);
      toast.success(`Đã xóa "${target.filename}" thành công.`);
      setConfirmDelete(null);
    } catch {
      toast.error("Không thể xóa CV. Vui lòng thử lại.");
    } finally {
      setIsDeleting(false);
    }
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
          <div className="mt-8 rounded-3xl border border-dashed border-gray-200 bg-white/80 p-8 md:p-12 text-center max-w-xl mx-auto shadow-xs">
            <div className="mx-auto w-14 h-14 rounded-2xl bg-[#EAF5EC] text-[#2D7A58] flex items-center justify-center mb-4">
              <FileText size={28} />
            </div>
            <h2 className="text-base font-bold text-slate-800">Bắt đầu với CV đầu tiên của bạn</h2>
            <p className="mt-2 text-xs text-gray-500 leading-relaxed max-w-md mx-auto">
              Tải file PDF CV hiện tại. Hệ thống sẽ bóc tách cấu trúc từng dòng, giúp bạn soát lỗi và tối ưu hoá câu từ phù hợp với yêu cầu tuyển dụng.
            </p>
            <button
              type="button"
              onClick={() => {
                setUploadError(null);
                setModalOpen(true);
              }}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[#2D7A58] px-5 py-2.5 text-xs font-bold text-white hover:bg-[#246347] shadow-sm cursor-pointer transition-colors"
            >
              <Plus size={15} />
              Tải lên CV (PDF)
            </button>
          </div>
        ) : (
          <motion.div
            className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4"
            variants={gridVariants}
            initial={reduceMotion ? false : "hidden"}
            animate="visible"
          >
            <AnimatePresence initial={false}>
            {cvList.map((cv, index) => (
              <motion.div
                key={cv.id}
                variants={cardVariants}
                custom={index}
                initial="hidden"
                animate="visible"
                exit="exit"
              >
              <CvCard
                id={cv.id}
                filename={cv.cv_filename}
                thumbnailFileId={cv.thumbnail_file_id ?? null}
                hasPdf={Boolean(cv.pdf_file_id || cv.thumbnail_file_id || cv.pdf_url)}
                text={cv.cv_text}
                createdAt={cv.created_at}
                onOpen={() => setActionId(cv.id)}
                onDelete={() => handleDeleteCV(cv.id, cv.cv_filename)}
              />
              </motion.div>
            ))}
            </AnimatePresence>
          </motion.div>
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

      {/* Action modal: choose review or features */}
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
                Chọn tính năng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* In-app confirmation modal for CV deletion (replaces native window.confirm) */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Xác nhận xóa CV">
          <button type="button" aria-label="Hủy xóa" onClick={() => !isDeleting && setConfirmDelete(null)} className="absolute inset-0 bg-slate-900/50 cursor-pointer" />
          <div className="relative w-full max-w-sm rounded-2xl bg-white p-5 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center shrink-0">
                <AlertTriangle size={20} />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-bold text-slate-900">Xóa bản CV này?</h3>
                <p className="mt-1 text-xs text-gray-500 leading-relaxed">
                  Bạn có chắc muốn xóa <span className="font-semibold text-slate-800 break-all">{confirmDelete.filename}</span>? Các bản CV đã tối ưu trong lịch sử sẽ không bị ảnh hưởng.
                </p>
              </div>
            </div>
            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setConfirmDelete(null)}
                className="rounded-xl border border-gray-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-gray-50 disabled:opacity-50 cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => void executeDeleteCV()}
                className="inline-flex items-center gap-1.5 rounded-xl bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700 disabled:opacity-50 cursor-pointer transition-colors"
              >
                {isDeleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                {isDeleting ? "Đang xóa..." : "Xác nhận xóa"}
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
    const diffMs = Date.now() - t;
    const mins = Math.max(0, Math.round(diffMs / 60000));
    if (mins < 1) return "Vừa xong";
    if (mins < 60) return `${mins} phút trước`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours} giờ trước`;
    const days = Math.round(hours / 24);
    if (days < 30) return `${days} ngày trước`;
    return new Date(createdAt).toLocaleDateString("vi-VN");
  } catch {
    return "";
  }
}

function CvCard({
  id,
  filename,
  thumbnailFileId,
  hasPdf,
  text,
  createdAt,
  onOpen,
  onDelete,
}: {
  id: string;
  filename: string;
  thumbnailFileId: string | null;
  hasPdf: boolean;
  text: string;
  createdAt: string;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const [thumbFailed, setThumbFailed] = useState(false);
  const [edited, setEdited] = useState("");

  useEffect(() => {
    setThumbFailed(false);
  }, [id, thumbnailFileId]);

  useEffect(() => {
    const frameId = requestAnimationFrame(() => {
      setEdited(formatRelativeTime(createdAt));
    });
    return () => cancelAnimationFrame(frameId);
  }, [createdAt]);

  const firstLine = text.split("\n").map((l) => l.trim()).filter(Boolean)[0] ?? "";
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      aria-label={`Mở CV ${filename}`}
      className="group overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xs cursor-pointer hover:border-[#2D7A58]/60 hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-[#2D7A58]/30"
    >
      <div className="aspect-1/1.25 overflow-hidden bg-[#F7F9F7] pointer-events-none relative">
        {hasPdf && !thumbFailed ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`/api/cv/${id}/thumbnail${thumbnailFileId ? `?v=${encodeURIComponent(thumbnailFileId)}` : ""}`}
            alt=""
            aria-hidden="true"
            className="h-full w-full object-cover object-top"
            loading="lazy"
            onError={() => setThumbFailed(true)}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-1.5 p-4 text-center">
            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400">
              <FileText size={20} />
            </div>
            <p className="line-clamp-3 text-[11px] font-semibold text-gray-500">{firstLine || filename}</p>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 border-t border-gray-100 px-3.5 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-slate-800 group-hover:text-[#2D7A58] transition-colors">{filename}</p>
          {edited && <p className="text-[11px] text-gray-400 mt-0.5">Đã sửa {edited}</p>}
        </div>
        <button
          type="button"
          aria-label={`Xóa ${filename}`}
          className="rounded-lg p-2 text-red-600/70 hover:text-red-700 hover:bg-red-50 shrink-0 cursor-pointer transition-colors relative after:absolute after:-inset-1"
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
