"use client";

import { Trash2 } from "lucide-react";
import type { CVUnknownBlock } from "@/types";

interface Props {
  block: CVUnknownBlock;
  onChange: (patch: Partial<CVUnknownBlock>) => void;
  onToggleHidden?: () => void;
}

export function UnknownForm({ block, onChange }: Props) {
  return (
    <div className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-600">
        Nội dung chưa được phân loại — độ tin cậy {(block.confidence * 100).toFixed(0)}%
      </p>
      <div className="space-y-2">
        {block.lines.map((line, index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              type="text"
              value={line}
              placeholder="Dòng"
              onChange={(e) => {
                const lines = block.lines.map((l, i) => (i === index ? e.target.value : l));
                onChange({ lines });
              }}
              className="flex-1 min-w-0 rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-800 focus:border-[#2D7A58] focus:outline-none focus:ring-2 focus:ring-[#2D7A58]/10 transition-all"
            />
            <button
              type="button"
              onClick={() => onChange({ lines: block.lines.filter((_, i) => i !== index) })}
              className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-[#B22222] transition-colors"
              aria-label="Xóa dòng"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => onChange({ lines: [...block.lines, ""] })}
          className="inline-flex items-center text-xs font-semibold text-[#2D7A58] hover:underline cursor-pointer pt-1"
        >
          + Thêm dòng
        </button>
      </div>
    </div>
  );
}