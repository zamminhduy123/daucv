"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  Columns2,
  Download,
  FileDiff,
  FileCheck,
  Loader2,
  Minus,
  Plus,
  RotateCcw,
  SlidersHorizontal,
  Type,
} from "lucide-react";
import { toast } from "sonner";

import { CVIframe } from "@/components/workspace/LocalCVPreview";
import ExportDiffList from "@/components/workspace/ExportDiffList";
import { CV_DESIGNS } from "@/lib/cv-designs";
import { diffDocuments } from "@/lib/cv-diff";
import { buildCVHtml, type CVTypographyConfig } from "@/lib/cv-render-html";
import { v1ToV2 } from "@/lib/cv-v1-to-v2-adapter";
import {
  downloadWysiwygPDFAPI,
  listTailoredCVVersionsAPI,
  updateTailoredCVDesignAPI,
} from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";
import { tailoredCVDisplayName } from "@/lib/tailored-cv";
import type { CVDesign, TailoredCVVersion } from "@/types";

type ExportView = "side-by-side" | "diff" | "final";

type ConcreteTypography = Omit<Required<CVTypographyConfig>, "fontSize" | "lineHeight"> & {
  lineHeight: number;
};

const DEFAULT_TYPOGRAPHY: ConcreteTypography = {
  fontFamily: "'Times New Roman'",
  baseFontSize: 9.5,
  lineHeight: 1.4,
  sectionSpacing: 4.0,
  itemSpacing: 3.0,
  pageMargin: 12,
};

function SpacingRow({
  label,
  value,
  unit = "",
  min,
  max,
  step,
  precision = 1,
  displayFormat,
  onChange,
}: {
  label: string;
  value: number;
  unit?: string;
  min: number;
  max: number;
  step: number;
  precision?: number;
  displayFormat?: (v: number) => string;
  onChange: (value: number) => void;
}) {
  const display = displayFormat ? displayFormat(value) : `${value.toFixed(precision)} ${unit}`.trim();
  const stepBy = (dir: -1 | 1) => {
    onChange(Math.min(max, Math.max(min, +(value + dir * step).toFixed(precision))));
  };
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs font-medium text-slate-700">
        <span>{label}</span>
        <span className="font-semibold text-slate-900">{display}</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="h-1.5 flex-1 cursor-pointer appearance-none rounded-lg bg-gray-200 accent-[#2D7A58]"
        />
        <div className="flex items-center rounded-lg border border-gray-200 bg-gray-50 p-0.5">
          <button
            type="button"
            onClick={() => stepBy(-1)}
            disabled={value <= min}
            className="flex h-5 w-5 cursor-pointer items-center justify-center rounded text-slate-600 hover:bg-white disabled:opacity-40"
            aria-label={`Giảm ${label}`}
          >
            <Minus size={11} />
          </button>
          <button
            type="button"
            onClick={() => stepBy(1)}
            disabled={value >= max}
            className="flex h-5 w-5 cursor-pointer items-center justify-center rounded text-slate-600 hover:bg-white disabled:opacity-40"
            aria-label={`Tăng ${label}`}
          >
            <Plus size={11} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ExportScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const selectedId = params.get("selected");

  const [versions, setVersions] = useState<TailoredCVVersion[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [design, setDesign] = useState<CVDesign>("classic_ats");
  const [isChangingDesign, setIsChangingDesign] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [view, setView] = useState<ExportView>("side-by-side");
  const [typography, setTypography] = useState<ConcreteTypography>(DEFAULT_TYPOGRAPHY);
  const [showSpacing, setShowSpacing] = useState(false);
  const spacingRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listTailoredCVVersionsAPI()
      .then(({ versions }) => {
        setVersions(versions);
        const current = selectedId ? versions.find((v) => v.id === selectedId) : versions[0];
        if (current) setDesign(current.selected_design);
      })
      .catch((err) => setLoadError(apiErrorMessage(err)));
  }, [selectedId]);

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (spacingRef.current && !spacingRef.current.contains(e.target as Node)) {
        setShowSpacing(false);
      }
    }
    if (showSpacing) document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, [showSpacing]);

  const selected = useMemo(() => {
    if (!versions) return undefined;
    return (selectedId ? versions.find((v) => v.id === selectedId) : versions[0]) ?? undefined;
  }, [versions, selectedId]);

  const beforeDoc = useMemo(() => {
    if (!selected) return null;
    if (selected.source_document_v2) return selected.source_document_v2;
    return null;
  }, [selected]);

  const afterDoc = useMemo(() => {
    if (!selected) return null;
    if (selected.document_v2) return selected.document_v2;
    const cv = selected.tailored_cv;
    return v1ToV2(cv.name, cv.headline, cv.contact_lines, cv.summary, cv.sections, cv.experience, cv.skills, cv.education);
  }, [selected]);

  const diffs = useMemo(() => diffDocuments(beforeDoc, afterDoc), [beforeDoc, afterDoc]);
  const language = selected?.source_language ?? "vi";

  const beforeHtml = useMemo(
    () => (beforeDoc ? buildCVHtml(beforeDoc, design, language, typography) : ""),
    [beforeDoc, design, language, typography],
  );
  const afterHtml = useMemo(
    () => (afterDoc ? buildCVHtml(afterDoc, design, language, typography) : ""),
    [afterDoc, design, language, typography],
  );

  const changeDesign = async (next: CVDesign) => {
    if (!selected || next === design) return;
    setDesign(next);
    setIsChangingDesign(true);
    try {
      const updated = await updateTailoredCVDesignAPI(selected.id, next);
      setVersions((items) => items?.map((v) => (v.id === updated.id ? updated : v)) ?? items);
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setDesign(selected.selected_design);
    } finally {
      setIsChangingDesign(false);
    }
  };

  // WYSIWYG download: the exact on-screen preview HTML (with live
  // typography) is rendered to PDF bytes server-side. What you see is
  // what downloads — no template differences, no print-dialog settings.
  const download = async () => {
    if (!selected || isDownloading || !afterHtml) return;
    setIsDownloading(true);
    try {
      const blob = await downloadWysiwygPDFAPI(selected.id, afterHtml);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      const label = [selected.target_role, selected.company_name].filter(Boolean).join("-") || "tailored-cv";
      anchor.href = url;
      anchor.download = `${label.replace(/[^a-zA-Z0-9À-ỹ_-]+/g, "-")}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Đã tải PDF thành công.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setIsDownloading(false);
    }
  };

  if (loadError) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-sm font-bold text-[#B22222]">Không thể tải CV đã tối ưu.</p>
        <p className="text-xs text-gray-500">{loadError}</p>
        <button
          type="button"
          onClick={() => router.push("/app/history")}
          className="cursor-pointer rounded-xl bg-[#2D7A58] px-4 py-2 text-xs font-bold text-white"
        >
          Về thư viện CV
        </button>
      </div>
    );
  }

  if (!versions || !selected || !afterDoc) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center gap-2 p-6">
        <Loader2 size={18} className="animate-spin text-[#2D7A58]" />
        <p className="text-sm font-medium text-gray-500">Đang chuẩn bị bản so sánh...</p>
      </div>
    );
  }

  const viewTabs: { value: ExportView; label: string; icon: typeof Columns2 }[] = [
    { value: "side-by-side", label: "Song song", icon: Columns2 },
    { value: "diff", label: `Diff (${diffs.length})`, icon: FileDiff },
    { value: "final", label: "Bản cuối", icon: FileCheck },
  ];

  return (
    <div className="flex h-full min-h-screen flex-col bg-[#FBFBFA] text-[#2F4F4F]">
      {/* Top toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 bg-white px-6 py-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/app/history")}
            className="rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-gray-100 hover:text-slate-800"
            title="Về thư viện CV"
            aria-label="Về thư viện CV"
          >
            <ArrowLeft size={17} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold tracking-tight text-slate-800">
                {tailoredCVDisplayName(selected)}
              </h1>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                  diffs.length > 0 ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"
                }`}
              >
                {diffs.length > 0 ? `${diffs.length} thay đổi` : "Không thay đổi"}
              </span>
            </div>
            <p className="mt-0.5 text-[11px] text-gray-400">
              Trước (CV đã sửa) → Sau (CV tối ưu) · chỉ thay đổi câu chữ được tô màu
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <select
            value={design}
            onChange={(e) => void changeDesign(e.target.value as CVDesign)}
            disabled={isChangingDesign}
            className="rounded-xl border border-gray-200/90 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-gray-300 focus:border-[#2D7A58] focus:outline-none disabled:opacity-60"
            aria-label="Chọn mẫu CV"
          >
            {CV_DESIGNS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={download}
            disabled={isDownloading}
            title="Tải đúng bản xem trước trên màn hình"
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-full bg-[#2D7A58] px-4 py-1.5 text-xs font-bold text-white shadow-xs transition-all hover:bg-[#246347] disabled:cursor-wait disabled:opacity-60"
          >
            {isDownloading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
            {isDownloading ? "Đang tạo PDF..." : "Tải PDF"}
          </button>
        </div>
      </div>

      {/* Sub-toolbar: view toggle + typography */}
      <div className="flex flex-wrap items-center gap-2.5 border-b border-gray-100 bg-white px-6 py-2">
        <div className="inline-flex items-center gap-1 rounded-xl border border-gray-200 bg-gray-50/60 p-1">
          {viewTabs.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setView(t.value)}
              aria-pressed={view === t.value}
              className={`inline-flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                view === t.value ? "bg-white text-[#2D7A58] shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              <t.icon size={13} />
              {t.label}
            </button>
          ))}
        </div>

        <div className="mx-0.5 h-4 w-px bg-gray-200" />

        <div className="relative">
          <select
            value={typography.fontFamily}
            onChange={(e) => setTypography((t) => ({ ...t, fontFamily: e.target.value }))}
            className="cursor-pointer appearance-none rounded-xl border border-gray-200 bg-white py-1.5 pl-8 pr-7 text-xs font-medium text-slate-700 hover:border-gray-300 focus:border-[#2D7A58] focus:outline-none"
            aria-label="Kiểu font chữ"
          >
            <option value="'Times New Roman'">Times New Roman</option>
            <option value="Inter">Inter</option>
            <option value="Roboto">Roboto</option>
            <option value="Georgia">Georgia</option>
            <option value="Merriweather">Merriweather</option>
            <option value="Arial">Arial</option>
          </select>
          <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-500">
            Aa
          </span>
          <ChevronDown size={12} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
        </div>

        <div className="inline-flex items-center rounded-xl border border-gray-200 bg-white p-0.5 shadow-2xs">
          <button
            type="button"
            onClick={() =>
              setTypography((t) => ({ ...t, baseFontSize: Math.max(8.0, +(t.baseFontSize - 0.5).toFixed(1)) }))
            }
            disabled={typography.baseFontSize <= 8.0}
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="Giảm cỡ chữ (0.5pt)"
            aria-label="Giảm cỡ chữ"
          >
            <Minus size={13} />
          </button>
          <div className="flex min-w-[58px] select-none items-center justify-center gap-1 px-2 text-xs font-semibold text-slate-700">
            <Type size={12} className="text-slate-400" />
            <span>{typography.baseFontSize.toFixed(1)} pt</span>
          </div>
          <button
            type="button"
            onClick={() =>
              setTypography((t) => ({ ...t, baseFontSize: Math.min(13.0, +(t.baseFontSize + 0.5).toFixed(1)) }))
            }
            disabled={typography.baseFontSize >= 13.0}
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="Tăng cỡ chữ (0.5pt)"
            aria-label="Tăng cỡ chữ"
          >
            <Plus size={13} />
          </button>
        </div>

        <div className="relative" ref={spacingRef}>
          <button
            type="button"
            onClick={() => setShowSpacing((v) => !v)}
            aria-expanded={showSpacing}
            className={`inline-flex cursor-pointer items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold shadow-2xs transition-all ${
              showSpacing
                ? "border-[#2D7A58] bg-[#EBF7EE] text-[#2D7A58]"
                : "border-gray-200 bg-white text-slate-700 hover:border-gray-300 hover:bg-slate-50"
            }`}
          >
            <SlidersHorizontal size={13} />
            <span>Giãn cách</span>
            <ChevronDown size={12} className={`text-gray-400 transition-transform ${showSpacing ? "rotate-180 text-[#2D7A58]" : ""}`} />
          </button>
          {showSpacing && (
            <div className="absolute left-0 top-full z-50 mt-2 w-80 rounded-2xl border border-gray-200 bg-white p-4 shadow-xl">
              <div className="mb-3 flex items-center justify-between border-b border-gray-100 pb-3">
                <span className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <SlidersHorizontal size={13} className="text-[#2D7A58]" />
                  Bố cục & Khoảng cách
                </span>
                <button
                  type="button"
                  onClick={() => setTypography((t) => ({ ...t, ...DEFAULT_TYPOGRAPHY }))}
                  className="inline-flex cursor-pointer items-center gap-1 text-[11px] font-medium text-slate-500 transition-colors hover:text-[#2D7A58]"
                >
                  <RotateCcw size={11} />
                  Mặc định
                </button>
              </div>
              <div className="space-y-3.5">
                <SpacingRow label="Khoảng cách phần" value={typography.sectionSpacing} unit="mm" min={0} max={10.0} step={0.5} onChange={(v) => setTypography((t) => ({ ...t, sectionSpacing: v }))} />
                <SpacingRow label="Khoảng cách mục" value={typography.itemSpacing} unit="mm" min={0} max={8.0} step={0.5} onChange={(v) => setTypography((t) => ({ ...t, itemSpacing: v }))} />
                <SpacingRow label="Độ giãn dòng" value={typography.lineHeight} unit="x" min={1.0} max={1.80} step={0.05} precision={2} displayFormat={(v) => `${v.toFixed(2)}x`} onChange={(v) => setTypography((t) => ({ ...t, lineHeight: v }))} />
                <SpacingRow label="Lề trang" value={typography.pageMargin} unit="mm" min={0} max={20} step={1} precision={0} onChange={(v) => setTypography((t) => ({ ...t, pageMargin: v }))} />
              </div>
              <div className="-mx-4 -mb-4 mt-3.5 rounded-b-2xl border-t border-gray-100 bg-[#F8FAF9] p-3 text-[11px] leading-relaxed text-slate-500">
                💡 <span className="font-medium text-slate-700">Mẹo:</span> Giảm khoảng cách mục hoặc lề trang nếu CV tràn sang trang 2 chỉ vài dòng.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 overflow-y-auto bg-[#EEF2EE] p-4 md:p-6">
        {view === "diff" && (
          <div className="mx-auto max-w-5xl">
            <ExportDiffList diffs={diffs} />
            <p className="mt-4 text-center text-[11px] text-slate-500">
              Chỉ những câu chữ nền xanh lá mới vào file PDF. Chuyển sang “Song song” để xem bố cục trang.
            </p>
          </div>
        )}

        {view === "side-by-side" && (
          <div className="mx-auto max-w-7xl">
            {diffs.length > 0 && (
              <div className="mb-4">
                <ExportDiffList diffs={diffs} />
              </div>
            )}
            <div className="grid items-start gap-4 lg:grid-cols-2">
              <div>
                <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-gray-500">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm bg-gray-400" />
                  Trước · CV đã sửa
                </p>
                {beforeHtml ? (
                  <CVIframe html={beforeHtml} />
                ) : (
                  <div className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center text-xs text-gray-400">
                    Không có bản gốc để so sánh.
                  </div>
                )}
              </div>
              <div>
                <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[#2D7A58]">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2D7A58]" />
                  Sau · CV tối ưu ({diffs.length} thay đổi)
                </p>
                <CVIframe html={afterHtml} />
              </div>
            </div>
          </div>
        )}

        {view === "final" && (
          <div className="mx-auto max-w-3xl">
            <CVIframe html={afterHtml} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function ExportPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[60vh] items-center justify-center gap-2 p-6">
          <Loader2 size={18} className="animate-spin text-[#2D7A58]" />
          <p className="text-sm font-medium text-gray-500">Đang chuẩn bị bản so sánh...</p>
        </div>
      }
    >
      <ExportScreen />
    </Suspense>
  );
}
