"use client";

import { Library, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { CV_DESIGN_LABELS } from "@/lib/cv-designs";
import type { TailoredCVVersion } from "@/types";

export default function TailoredCVLibrary({ versions, selectedId, onSelect, onDelete, onCreate }: { versions: TailoredCVVersion[]; selectedId: string | null; onSelect: (id: string) => void; onDelete: (id: string) => void; onCreate: () => void }) {
  return <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
    <section className="rounded-3xl border border-[#2F4F4F]/5 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2"><Library size={20} className="text-[#6A9B5E]" /><h2 className="text-lg font-black">Thư viện CV</h2></div>
        <span className="rounded bg-gray-50 px-2 py-1 text-xs font-bold text-gray-400">{versions.length} bản lưu</span>
      </div>
      <div className="space-y-2">
        {versions.map((version) => <div key={version.id} className={`group rounded-xl border p-3 transition ${selectedId === version.id ? "border-[#6A9B5E]/20 bg-[#6A9B5E]/5" : "border-transparent hover:bg-gray-50"}`}>
          <button type="button" onClick={() => onSelect(version.id)} className="flex w-full items-center gap-3 text-left">
            <span className={`h-2 w-2 rounded-full ${selectedId === version.id ? "bg-[#6A9B5E]" : "bg-gray-300"}`} />
            <span className="min-w-0 flex-1">
              <span className={`block truncate text-sm font-black ${selectedId === version.id ? "text-[#6A9B5E]" : "text-[#2F4F4F]"}`}>{version.target_role || "CV đã tối ưu"}</span>
              <span className="mt-1 flex flex-wrap items-center gap-2 text-[10px] font-bold text-gray-400">
                <span className="rounded bg-gray-100 px-1.5 py-0.5 uppercase">{CV_DESIGN_LABELS[version.selected_design]}</span>
                <span>{version.company_name || new Date(version.created_at).toLocaleDateString("vi-VN")}</span>
              </span>
            </span>
          </button>
          <button type="button" onClick={() => onDelete(version.id)} className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-[#B22222] opacity-80 transition hover:opacity-100"><Trash2 size={13} />Xóa</button>
        </div>)}
        <button type="button" onClick={onCreate} className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-100 p-4 text-sm font-bold text-gray-400 transition hover:border-[#6A9B5E]/50 hover:text-[#6A9B5E]"><Plus size={16} />Phân tích CV mới</button>
      </div>
    </section>
    <section className="rounded-3xl border border-[#6A9B5E]/10 bg-[#6A9B5E]/5 p-5">
      <div className="mb-3 flex items-center gap-2 text-[#6A9B5E]"><ShieldCheck size={18} /><span className="text-xs font-black uppercase tracking-widest">Bảo toàn nội dung</span></div>
      <p className="text-xs font-bold leading-relaxed text-[#2F4F4F]">CV mới giữ nguyên ngôn ngữ gốc và chỉ áp dụng các thay đổi an toàn từ phân tích LLM.</p>
      <p className="mt-2 text-[11px] font-medium leading-relaxed text-gray-500">Đổi mẫu và tải xuống không tốn thêm tín dụng.</p>
    </section>
  </aside>;
}
