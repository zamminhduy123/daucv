"use client";

import type { CVSkillGroupBlock } from "@/types";

interface Props {
  block: CVSkillGroupBlock;
  onChange: (patch: Partial<CVSkillGroupBlock>) => void;
  onToggleHidden?: () => void;
}

export function SkillGroupForm({ block, onChange }: Props) {
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <label className="text-xs font-semibold text-slate-700">Tên nhóm kỹ năng</label>
        <input
          type="text"
          value={block.label ?? ""}
          placeholder="Ví dụ: AI Engineering, Backend / Deployment..."
          onChange={(e) => onChange({ label: e.target.value })}
          className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm font-semibold text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-700">Danh sách kỹ năng</label>
        <div className="flex flex-wrap items-center gap-1.5 min-h-[36px] p-2 rounded-xl border border-gray-200/80 bg-gray-50/50">
          {(block.skills ?? []).length === 0 ? (
            <span className="text-xs text-gray-400 italic">Chưa có kỹ năng nào. Nhập bên dưới và nhấn Enter.</span>
          ) : (
            (block.skills ?? []).map((skill, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1.5 rounded-full bg-[#EAF5EC] px-3 py-1 text-xs font-medium text-[#2D7A58] border border-[#6A9B5E]/30"
              >
                {skill}
                <button
                  type="button"
                  onClick={() => onChange({ skills: block.skills.filter((_, i) => i !== index) })}
                  className="text-gray-400 hover:text-red-600 transition-colors"
                  aria-label="Xóa kỹ năng"
                >
                  ✕
                </button>
              </span>
            ))
          )}
        </div>
        <input
          type="text"
          placeholder="Nhập kỹ năng rồi nhấn Enter để thêm (VD: PyTorch, FastAPI, Docker...)"
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            e.preventDefault();
            const value = e.currentTarget.value.trim();
            if (!value) return;
            onChange({ skills: [...(block.skills ?? []), value] });
            e.currentTarget.value = "";
          }}
          className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none transition-colors"
        />
      </div>
    </div>
  );
}