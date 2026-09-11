"use client";

import type { BlockDiff, WordToken } from "@/lib/cv-diff";

function DiffTokens({ tokens, side }: { tokens: WordToken[]; side: "del" | "add" }) {
  return (
    <span>
      {tokens.map((t, i) => {
        if (t.kind === "same") return <span key={i}>{t.text}</span>;
        const highlight =
          side === "del" ? "bg-red-300/70 text-red-950 rounded px-0.5" : "bg-green-300/70 text-green-950 rounded px-0.5";
        return (
          <span key={i} className={highlight}>
            {t.text}
          </span>
        );
      })}
    </span>
  );
}

/**
 * GitHub-style unified diff list for the export screen.
 * Each changed bullet/paragraph renders as a red (before) / green (after)
 * row pair with word-level highlights, grouped under its section.
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
        <div key={section} className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 bg-gray-50/80 px-4 py-2">
            <span className="text-xs font-bold text-slate-800">{section}</span>
            <span className="rounded-full bg-gray-200/70 px-2 py-0.5 text-[11px] font-bold text-slate-600">
              {items.length} thay đổi
            </span>
          </div>
          <div className="divide-y divide-gray-100">
            {items.map((d) => (
              <div key={d.id} className="grid grid-cols-1 md:grid-cols-2">
                <div className="border-l-4 border-l-red-400 bg-red-50/60 px-4 py-3">
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-red-500">
                    Trước · {d.label}
                  </p>
                  <p className="text-[13px] leading-relaxed text-slate-800">
                    <DiffTokens tokens={d.beforeWords} side="del" />
                  </p>
                </div>
                <div className="border-l-4 border-l-green-500 bg-green-50/60 px-4 py-3 md:border-l md:border-l-green-500">
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-green-600">
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
