"use client";

import type { CVPublicationBlock } from "@/types";

interface Props {
  block: CVPublicationBlock;
  onChange: (patch: Partial<CVPublicationBlock>) => void;
  onToggleHidden?: () => void;
}

export function PublicationForm({ block, onChange }: Props) {
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <label className="text-xs font-semibold text-slate-700">Tiêu đề bài báo / ấn phẩm</label>
        <input
          type="text"
          value={block.title}
          placeholder="Ví dụ: Deep Learning for Low-light Image Enhancement"
          onChange={(e) => onChange({ title: e.target.value })}
          className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm font-semibold text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
        />
      </div>
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Tác giả</label>
          <input
            type="text"
            value={block.authors ?? ""}
            placeholder="Ví dụ: Minh Duy Nguyen, Tien Nguyen"
            onChange={(e) => onChange({ authors: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Nơi công bố / Hội nghị / Tạp chí</label>
          <input
            type="text"
            value={block.venue ?? ""}
            placeholder="Ví dụ: IEEE CVPR / Springer"
            onChange={(e) => onChange({ venue: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Thời gian</label>
          <input
            type="text"
            value={block.date ?? ""}
            placeholder="Ví dụ: 2024"
            onChange={(e) => onChange({ date: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">Trạng thái (tùy chọn)</label>
          <input
            type="text"
            value={block.status ?? ""}
            placeholder="Ví dụ: Accepted / Under Review"
            onChange={(e) => onChange({ status: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
          />
        </div>
      </div>
    </div>
  );
}