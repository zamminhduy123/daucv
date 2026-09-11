"use client";

import type { BlockDiff, WordToken } from "@/lib/cv-diff";

function DiffTokens({ tokens, side }: { tokens: WordToken[]; side: "del" | "add" }) {
  return (
    <span>
      {tokens.map((t, i) => {
        if (t.kind === "same") return <span key={i}>{t.text}</span>;
        if (side === "del") {
          return (
            <del key={i} className="no-line-through bg-red-200/80 text-red-950 rounded px-1 py-0.5 font-medium">
              <span className="sr-only">Nội dung cũ: </span>
              {t.text}
            </del>
          );
        }
        return (
          <ins key={i} className="no-underline bg-emerald-200/80 text-emerald-950 rounded px-1 py-0.5 font-medium">
            <span className="sr-only">Nội dung mới: </span>
            {t.text}
          </ins>
        );
      })}
    </span>
  );
}

/**
 * Clean semantic diff list for the export screen.
 * Each changed bullet/paragraph renders as a before/after row pair
 * with word-level highlights using semantic <del> / <ins>, grouped under its section.
 */
export default function ExportDiffList({ diffs }: { diffs: BlockDiff[] }) {
  if (diffs.length === 0) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-6 text-center">
        <p className="text-sm font-bold text-emerald-900">CV đã ổn — không có thay đổi nào.</p>
        <p className="mt-1 text-xs text-emerald-700">
          Bản sau giữ nguyên từng câu chữ của CV gốc. Bạn vẫn có thể chỉnh giãn cách và tải PDF.
        </p>
      </div>
    );
  }

  const grouped = new Map<string, BlockDiff[]>();
  for (const d of diffs) {
    const list = grouped.get(d.sectionTitle) ?? [];
    list.push(d);
    grouped.set(d.sectionTitle, list);
  }

  return (
    <div className="space-y-4">
      {[...grouped.entries()].map(([section, items]) => (
        <div key={section} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xs">
          <div className="flex items-center justify-between border-b border-gray-100 bg-gray-50/80 px-4 py-2">
            <span className="text-xs font-bold text-slate-800">{section}</span>
            <span className="rounded-full bg-gray-200/70 px-2 py-0.5 text-[11px] font-bold text-slate-600">
              {items.length} thay đổi
            </span>
          </div>
          <div className="divide-y divide-gray-100">
            {items.map((d) => (
              <div key={d.id} className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-100">
                <div className="bg-red-50/30 px-4 py-3">
                  <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold text-red-700">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500" />
                    Trước · {d.label}
                  </p>
                  <p className="text-[13px] leading-relaxed text-slate-800">
                    <DiffTokens tokens={d.beforeWords} side="del" />
                  </p>
                </div>
                <div className="bg-emerald-50/30 px-4 py-3">
                  <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold text-emerald-800">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#2D7A58]" />
                    Sau · {d.label}
                  </p>
                  <p className="text-[13px] leading-relaxed text-slate-900">
                    <DiffTokens tokens={d.afterWords} side="add" />
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
