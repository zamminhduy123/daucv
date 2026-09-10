"use client";

import type { CVParagraphBlock } from "@/types";

interface Props {
  block: CVParagraphBlock;
  onChange: (patch: Partial<CVParagraphBlock>) => void;
  onToggleHidden?: () => void;
}

export function ParagraphForm({ block, onChange }: Props) {
  return (
    <div className="w-full">
      <textarea
        value={block.text}
        placeholder="Nhập nội dung..."
        rows={3}
        onChange={(e) => onChange({ text: e.target.value })}
        className="w-full resize-y rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:outline-none focus:ring-2 focus:ring-[#2D7A58]/10 transition-all"
      />
    </div>
  );
}