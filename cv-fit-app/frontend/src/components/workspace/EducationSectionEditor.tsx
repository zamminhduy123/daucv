"use client";

import { Trash2 } from "lucide-react";
import type { CVEducationBlock } from "@/types";

interface Props {
  block: CVEducationBlock;
  onChange: (patch: Partial<CVEducationBlock>) => void;
  onToggleHidden?: () => void;
}

export function EducationForm({ block, onChange }: Props) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Trường / Cơ sở đào tạo</label>
          <input
            type="text"
            value={block.institution ?? ""}
            placeholder="Ví dụ: Đại học Bách Khoa Hà Nội"
            onChange={(e) => onChange({ institution: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm font-semibold text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Bằng cấp / Trình độ</label>
          <input
            type="text"
            value={block.degree ?? ""}
            placeholder="Ví dụ: Cử nhân / Thạc sĩ"
            onChange={(e) => onChange({ degree: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Chuyên ngành</label>
          <input
            type="text"
            value={block.field ?? ""}
            placeholder="Ví dụ: Khoa học máy tính"
            onChange={(e) => onChange({ field: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Thời gian</label>
          <input
            type="text"
            value={block.date ?? ""}
            placeholder="Ví dụ: 2019 - 2023"
            onChange={(e) => onChange({ date: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1 sm:col-span-2">
          <label className="text-xs font-semibold text-slate-700">Địa điểm</label>
          <input
            type="text"
            value={block.location ?? ""}
            placeholder="Ví dụ: Hà Nội, Việt Nam"
            onChange={(e) => onChange({ location: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
      </div>
      <div>
        <p className="mb-1.5 text-xs font-semibold text-slate-700">Chi tiết bổ sung (GPA, Giải thưởng, Khóa luận...)</p>
        <div className="space-y-2">
          {block.details.map((detail, index) => (
            <div key={index} className="flex items-center gap-2">
              <input
                type="text"
                value={detail}
                placeholder="Ví dụ: GPA: 3.8/4.0, Học bổng xuất sắc..."
                onChange={(e) => {
                  const details = block.details.map((d, i) => (i === index ? e.target.value : d));
                  onChange({ details });
                }}
                className="flex-1 rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-1.5 text-sm text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => onChange({ details: block.details.filter((_, i) => i !== index) })}
                className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-[#B22222] transition-colors"
                aria-label="Xóa chi tiết"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => onChange({ details: [...block.details, ""] })}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#2D7A58] hover:underline pt-1"
          >
            + Thêm chi tiết
          </button>
        </div>
      </div>
    </div>
  );
}