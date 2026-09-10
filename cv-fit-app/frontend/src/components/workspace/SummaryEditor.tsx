"use client";

import type { CVParagraphBlock } from "@/types";
import PrivacyToggle from "./PrivacyToggle";

interface Props {
  summary: CVParagraphBlock | null;
  onChange: (text: string) => void;
  onToggleHidden: () => void;
  hidden: boolean;
}

/** Auto-added "Summary" tab. A skipped-empty summary does not export: the
 *  parent page drops it before saving when text is empty AND not hidden. */
export default function SummaryEditor({ summary, onChange, onToggleHidden, hidden }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <label className="text-xs font-semibold text-slate-700">Tóm tắt giới thiệu bản thân</label>
          <p className="text-[11px] text-gray-400">
            Giới thiệu ngắn gọn 2–3 câu về năng lực chuyên môn và mục tiêu sự nghiệp.
          </p>
        </div>
        <PrivacyToggle
          hidden={hidden}
          onToggle={onToggleHidden}
          label="tóm tắt"
        />
      </div>
      <textarea
        value={summary?.text ?? ""}
        placeholder="Ví dụ: AI and machine learning researcher with a master's degree and hands-on experience developing Transformers, graph neural networks..."
        rows={6}
        onChange={(e) => onChange(e.target.value)}
        className="w-full resize-y rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white p-3.5 text-sm text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:ring-2 focus:ring-[#2D7A58]/10 focus:outline-none leading-relaxed transition-colors"
      />
      {hidden && (
        <p className="flex items-center gap-1.5 text-[11px] text-amber-600">
          Tóm tắt này đang được ẩn khỏi bản in CV.
        </p>
      )}
    </div>
  );
}