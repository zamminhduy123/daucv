"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, FileCheck, FileDiff, Loader2, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { toast } from "sonner";
import type { TailoredCVVersion } from "@/types";
import { deleteTailoredCVVersionAPI, listTailoredCVVersionsAPI } from "@/lib/api";
import { CV_DESIGN_LABELS } from "@/lib/cv-designs";
import { diffDocuments } from "@/lib/cv-diff";
import { apiErrorMessage } from "@/lib/errorMessages";
import { tailoredCVDisplayName } from "@/lib/tailored-cv";

function changeCount(version: TailoredCVVersion): number | null {
  if (!version.source_document_v2 || !version.document_v2) return null;
  try {
    return diffDocuments(version.source_document_v2, version.document_v2).length;
  } catch {
    return null;
  }
}

const listVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.05,
      duration: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 14 },
  visible: (index: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.05 + index * 0.06, duration: 0.35, ease: [0.25, 0.1, 0.25, 1] as const },
  }),
  exit: {
    opacity: 0,
    scale: 0.97,
    transition: { duration: 0.2 },
  },
};

export default function HistoryPage() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const [versions, setVersions] = useState<TailoredCVVersion[] | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    listTailoredCVVersionsAPI()
      .then(({ versions }) => setVersions(versions))
      .catch(() => setVersions([]));
  }, []);

  const sorted = useMemo(
    () =>
      (versions ?? []).slice().sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
    [versions],
  );

  const remove = async (id: string) => {
    setIsDeleting(true);
    try {
      await deleteTailoredCVVersionAPI(id);
      setVersions((items) => (items ?? []).filter((item) => item.id !== id));
      toast.success("Đã xóa bản CV đã tối ưu.");
      setConfirmDeleteId(null);
    } catch (error) {
      toast.error(apiErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  };

  const openExport = (id: string) => router.push(`/app/export?selected=${id}`);

  return (
    <div className="min-h-screen pb-12 text-[#2F4F4F]">
      <div className="mx-auto w-full space-y-6 p-4">
        <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#2D7A58]/10 text-[#2D7A58] shadow-sm">
              <FileCheck size={32} />
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight md:text-4xl">CV đã tối ưu</h1>
              <p className="mt-1 max-w-2xl text-sm font-medium text-gray-500">
                {sorted.length > 0
                  ? `${sorted.length} bản đã lưu — chọn một bản để so sánh trước/sau và xuất PDF.`
                  : "Các bản CV tối ưu của bạn sẽ xuất hiện tại đây."}
              </p>
            </div>
          </div>
          <button
            onClick={() => router.push("/app/setup")}
            className="inline-flex w-fit cursor-pointer items-center gap-2 rounded-2xl bg-[#2D7A58] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#2D7A58]/20 transition hover:bg-[#246347] active:scale-95"
          >
            <Plus size={18} />
            Phân tích CV mới
          </button>
        </header>

        {versions === null && (
          <div className="flex items-center justify-center gap-2 rounded-3xl border border-[#2F4F4F]/5 bg-white/70 p-12">
            <Loader2 size={18} className="animate-spin text-[#2D7A58]" />
            <p className="text-sm font-medium text-gray-500">Đang tải danh sách...</p>
          </div>
        )}

        {versions !== null && versions.length === 0 && (
          <div className="rounded-3xl border-2 border-dashed border-[#2F4F4F]/10 bg-white/70 p-12 text-center">
            <p className="font-bold text-[#2F4F4F]">Bạn chưa có CV đã tối ưu nào.</p>
            <p className="mt-1 text-sm text-gray-500">Chạy phân tích một CV để tạo bản tối ưu đầu tiên.</p>
            <button
              onClick={() => router.push("/app/setup")}
              className="mt-5 inline-flex cursor-pointer items-center gap-2 rounded-2xl bg-[#2D7A58] px-6 py-3 text-sm font-bold text-white shadow-lg shadow-[#2D7A58]/20 transition hover:bg-[#246347] active:scale-95"
            >
              <Plus size={18} />
              Phân tích CV mới
            </button>
          </div>
        )}

        {sorted.length > 0 && (
          <motion.ul
            className="space-y-3"
            variants={listVariants}
            initial={reduceMotion ? false : "hidden"}
            animate="visible"
          >
            <AnimatePresence initial={false}>
            {sorted.map((version, index) => {
              const count = changeCount(version);
              return (
                <motion.li
                  key={version.id}
                  variants={itemVariants}
                  custom={index}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  className="group flex flex-col gap-3 rounded-2xl border border-[#2F4F4F]/5 bg-white p-4 shadow-sm transition hover:border-[#2D7A58]/30 hover:shadow-md md:flex-row md:items-center md:justify-between"
                >
                  <button
                    type="button"
                    onClick={() => openExport(version.id)}
                    className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 text-left"
                  >
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#2D7A58]" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-base font-black text-[#2F4F4F]">
                        {tailoredCVDisplayName(version)}
                      </span>
                      <span className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] font-bold text-gray-400">
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 uppercase">
                          {CV_DESIGN_LABELS[version.selected_design] ?? version.selected_design}
                        </span>
                        <span>{new Date(version.created_at).toLocaleDateString("vi-VN")}</span>
                        {count !== null && (
                          <span
                            className={`rounded-full px-2 py-0.5 ${
                              count > 0 ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500"
                            }`}
                          >
                            {count > 0 ? `${count} thay đổi` : "Không thay đổi"}
                          </span>
                        )}
                      </span>
                    </span>
                    <ArrowRight
                      size={18}
                      className="shrink-0 text-gray-300 transition group-hover:translate-x-0.5 group-hover:text-[#2D7A58]"
                    />
                  </button>
                  <span className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openExport(version.id)}
                      className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl bg-[#2D7A58] px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-[#246347] active:scale-95"
                    >
                      <FileDiff size={14} />
                      So sánh & Xuất
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(version.id)}
                      className="cursor-pointer rounded-xl p-2 text-red-600/70 transition hover:bg-red-50 hover:text-red-700"
                      aria-label="Xóa CV"
                    >
                      <Trash2 size={18} />
                    </button>
                  </span>
                </motion.li>
              );
            })}
            </AnimatePresence>
          </motion.ul>
        )}

        {sorted.length > 0 && (
          <section className="flex items-start gap-3 rounded-3xl border border-[#2D7A58]/10 bg-[#2D7A58]/5 p-5">
            <ShieldCheck size={18} className="mt-0.5 shrink-0 text-[#2D7A58]" />
            <div>
              <p className="text-xs font-black uppercase tracking-widest text-[#2D7A58]">
                Bảo toàn nội dung
              </p>
              <p className="mt-1 text-xs font-bold leading-relaxed text-[#2F4F4F]">
                CV mới giữ nguyên ngôn ngữ gốc và chỉ áp dụng các thay đổi an toàn từ phân tích LLM.
              </p>
              <p className="mt-1 text-[11px] font-medium leading-relaxed text-gray-500">
                Đổi mẫu và tải xuống không tốn thêm tín dụng.
              </p>
            </div>
          </section>
        )}
      </div>

      {/* In-app delete confirmation modal */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Xác nhận xóa CV đã tối ưu">
          <button type="button" aria-label="Hủy xóa" onClick={() => !isDeleting && setConfirmDeleteId(null)} className="absolute inset-0 bg-slate-900/50 cursor-pointer" />
          <div className="relative w-full max-w-sm rounded-2xl bg-white p-5 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center shrink-0">
                <Trash2 size={20} />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-bold text-slate-900">Xóa bản CV đã tối ưu?</h3>
                <p className="mt-1 text-xs text-gray-500 leading-relaxed">
                  Bản CV đã tối ưu này sẽ bị xóa khỏi lịch sử. CV gốc trong thư viện của bạn không bị ảnh hưởng.
                </p>
              </div>
            </div>
            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setConfirmDeleteId(null)}
                className="rounded-xl border border-gray-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-gray-50 disabled:opacity-50 cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => void remove(confirmDeleteId)}
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
