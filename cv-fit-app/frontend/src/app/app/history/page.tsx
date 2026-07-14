"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, FileCheck, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { CVDesign, TailoredCVVersion } from "@/types";
import { deleteTailoredCVVersionAPI, downloadTailoredCVPDFAPI, listTailoredCVVersionsAPI, updateTailoredCVDesignAPI } from "@/lib/api";
import { CV_DESIGN_LABELS } from "@/lib/cv-designs";
import { apiErrorMessage } from "@/lib/errorMessages";
import { tailoredCVDisplayName } from "@/lib/tailored-cv";
import CVDesignSelector from "@/components/workspace/CVDesignSelector";
import TailoredCVLibrary from "@/components/workspace/TailoredCVLibrary";
import TailoredCVPreview from "@/components/workspace/TailoredCVPreview";

export default function HistoryPage() {
  const params = useSearchParams();
  const router = useRouter();
  const [versions, setVersions] = useState<TailoredCVVersion[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("preview"));
  const [isChangingDesign, setIsChangingDesign] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  useEffect(() => { listTailoredCVVersionsAPI().then(({ versions }) => { setVersions(versions); setSelectedId((current) => current || versions[0]?.id || null); }).catch(() => setVersions([])); }, []);
  const selected = versions.find((version) => version.id === selectedId);
  const changeDesign = async (design: CVDesign) => {
    if (!selected || design === selected.selected_design) return;
    setIsChangingDesign(true);
    try {
      const updated = await updateTailoredCVDesignAPI(selected.id, design);
      setVersions((items) => items.map((item) => item.id === updated.id ? updated : item));
    } catch (error) {
      toast.error(apiErrorMessage(error));
    } finally {
      setIsChangingDesign(false);
    }
  };
  const download = async (version: TailoredCVVersion) => { setDownloadingId(version.id); try { const blob = await downloadTailoredCVPDFAPI(version.id); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); const label = [version.target_role, version.company_name].filter(Boolean).join("-") || "tailored-cv"; anchor.href = url; anchor.download = `${label.replace(/[^a-zA-Z0-9À-ỹ_-]+/g, "-")}.pdf`; anchor.click(); URL.revokeObjectURL(url); } catch (error) { toast.error(apiErrorMessage(error)); } finally { setDownloadingId(null); } };
  const remove = async (id: string) => {
    if (!confirm("Xóa CV đã tối ưu này? CV gốc của bạn sẽ không bị ảnh hưởng.")) return;
    try {
      await deleteTailoredCVVersionAPI(id);
      const remaining = versions.filter((item) => item.id !== id);
      setVersions(remaining);
      if (selectedId === id) setSelectedId(remaining[0]?.id || null);
    } catch (error) {
      toast.error(apiErrorMessage(error));
    }
  };
  return <div className="min-h-screen pb-12 text-[#2F4F4F]">
    <div className="mx-auto w-full max-w-7xl space-y-8 p-4 ">
      <header className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#6A9B5E]/10 text-[#6A9B5E] shadow-sm">
            <FileCheck size={32} />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight md:text-4xl">CV đã tối ưu</h1>
            <p className="mt-1 max-w-2xl text-sm font-medium text-gray-500">Xem trước, đổi mẫu và tải xuống CV được cá nhân hóa theo vị trí ứng tuyển.</p>
          </div>
        </div>
        <div className="inline-flex w-fit items-center gap-2 rounded-2xl border border-[#6A9B5E]/20 bg-[#6A9B5E]/5 px-4 py-2 text-sm font-bold text-[#6A9B5E]">
          <ShieldCheck size={18} />
          <span>Preview + download sau phân tích</span>
        </div>
      </header>

      {!versions.length && <div className="rounded-3xl border-2 border-dashed border-[#2F4F4F]/10 bg-white/70 p-12 text-center">
        <p className="font-bold text-[#2F4F4F]">Bạn chưa có CV đã tối ưu nào.</p>
        <button onClick={() => router.push("/app/setup")} className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-[#6A9B5E] px-6 py-3 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:bg-[#5a874e] active:scale-95">
          <Plus size={18} />
          Phân tích CV mới
        </button>
      </div>}

      {versions.length > 0 && <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px]">
        {selected && <main className="min-w-0 overflow-hidden rounded-3xl border border-[#2F4F4F]/5 bg-white shadow-md">
          <div className="flex flex-col gap-4 border-b border-[#2F4F4F]/5 p-5 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-xl font-black">{tailoredCVDisplayName(selected)}</h2>
              <p className="mt-1 text-xs font-bold uppercase tracking-widest text-gray-400">{CV_DESIGN_LABELS[selected.selected_design]} · {new Date(selected.created_at).toLocaleDateString("vi-VN")}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={() => download(selected)} disabled={downloadingId === selected.id} className="inline-flex items-center gap-2 rounded-xl bg-[#6A9B5E] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:bg-[#5a874e] active:scale-95 disabled:cursor-wait disabled:opacity-70">
                <Download size={18} />
                {downloadingId === selected.id ? "Đang tạo PDF..." : "Tải PDF"}
              </button>
              <button onClick={() => remove(selected.id)} className="rounded-xl p-2.5 text-[#B22222] transition hover:bg-[#B22222]/5" aria-label="Xóa CV">
                <Trash2 size={20} />
              </button>
            </div>
          </div>

          <div className="border-b border-[#2F4F4F]/5 bg-gray-50/50 p-5">
            <p className="mb-4 text-xs font-black uppercase tracking-widest text-gray-400">Chọn mẫu CV</p>
            <CVDesignSelector selected={selected.selected_design} onChange={changeDesign} disabled={isChangingDesign} />
          </div>

          <div className="bg-[#f1f3f0] p-4 sm:p-8">
            <div className="mx-auto w-full transition duration-300 hover:scale-[1.005]">
              <TailoredCVPreview cv={selected.tailored_cv} design={selected.selected_design} language={selected.source_language ?? "vi"} onDownload={() => download(selected)} />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 border-t border-[#2F4F4F]/5 p-5">
            <button onClick={() => download(selected)} disabled={downloadingId === selected.id} className="inline-flex items-center gap-2 rounded-2xl bg-[#6A9B5E] px-8 py-3 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:scale-105 active:scale-95 disabled:cursor-wait disabled:opacity-70">
              <Download size={20} />
              {downloadingId === selected.id ? "Đang tạo PDF..." : "Tải PDF miễn phí"}
            </button>
          </div>
        </main>}

        <TailoredCVLibrary versions={versions} selectedId={selectedId} onSelect={setSelectedId} onDelete={remove} onCreate={() => router.push("/app/setup")} />
      </div>}
    </div>
  </div>;
}
