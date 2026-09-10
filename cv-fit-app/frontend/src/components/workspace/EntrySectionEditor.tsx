"use client";

import { Plus, Trash2 } from "lucide-react";
import type { CVEntryBlock } from "@/types";

interface EntryFormProps {
  block: CVEntryBlock;
  onChange: (patch: Partial<CVEntryBlock>) => void;
  onToggleHidden?: () => void;
}

export function EntryForm({ block, onChange }: EntryFormProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Chức vụ / Tiêu đề</label>
          <input
            type="text"
            value={block.title}
            placeholder="Ví dụ: AI Engineer / ML Engineer"
            onChange={(e) => onChange({ title: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm font-semibold text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Tổ chức / Công ty</label>
          <input
            type="text"
            value={block.organization ?? ""}
            placeholder="Ví dụ: VinAI Research / Đại học Bách Khoa"
            onChange={(e) => onChange({ organization: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Thời gian</label>
          <input
            type="text"
            value={block.date ?? ""}
            placeholder="Ví dụ: 2023 - Hiện tại"
            onChange={(e) => onChange({ date: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Địa điểm</label>
          <input
            type="text"
            value={block.location ?? ""}
            placeholder="Ví dụ: Hà Nội, Việt Nam"
            onChange={(e) => onChange({ location: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1 sm:col-span-2">
          <label className="text-xs font-semibold text-slate-700">Phụ đề (tùy chọn)</label>
          <input
            type="text"
            value={block.subtitle ?? ""}
            placeholder="Ví dụ: Dự án phát sinh / Mô tả ngắn"
            onChange={(e) => onChange({ subtitle: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-600 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
      </div>
      <div>
        <p className="mb-1.5 text-xs font-semibold text-slate-700">Các điểm mô tả chính (Bullets)</p>
        <div className="space-y-2">
          {block.bullets.map((bullet, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="text-[#2D7A58] font-bold text-xs">•</span>
              <input
                type="text"
                value={bullet}
                placeholder="Mô tả kết quả đạt được, số liệu cụ thể..."
                onChange={(e) => {
                  const bullets = block.bullets.map((b, i) => (i === index ? e.target.value : b));
                  onChange({ bullets });
                }}
                className="flex-1 rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-1.5 text-sm text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => onChange({ bullets: block.bullets.filter((_, i) => i !== index) })}
                className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-[#B22222] transition-colors"
                aria-label="Xóa dòng"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => onChange({ bullets: [...block.bullets, ""] })}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#2D7A58] hover:underline pt-1"
          >
            <Plus size={13} />
            Thêm dòng mô tả
          </button>
        </div>
      </div>
    </div>
  );
}