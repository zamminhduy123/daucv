"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { CV_DESIGN_LABELS } from "@/lib/cv-designs";
import { buildCVHtml, compactRenderingWarnings } from "@/lib/cv-render-html";
import { v1ToV2 } from "@/lib/cv-v1-to-v2-adapter";
import { fetchTailoredCVPreviewAPI } from "@/lib/api";
import { CURRENT_RECONSTRUCTION_VERSION } from "@/types";
import type { CVDesign, CVDocumentV2, CVRenderDiagnostics, TailoredCV } from "@/types";

function CVIframe({ html }: { html: string }) {
  const sensorRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [scale, setScale] = useState(1);
  const [height, setHeight] = useState(1123);

  useLayoutEffect(() => {
    const sensor = sensorRef.current;
    if (!sensor) return;
    const resize = () => setScale(Math.min(1, sensor.clientWidth / 794 || 1));
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(sensor);
    return () => observer.disconnect();
  }, []);

  const measureDocument = () => {
    const body = iframeRef.current?.contentDocument?.body;
    if (body) setHeight(Math.max(1123, body.scrollHeight));
  };

  return (
    <div className="relative flex w-full justify-center">
      <div ref={sensorRef} className="pointer-events-none invisible absolute inset-x-0" />
      <div className="overflow-hidden rounded-sm bg-white shadow-xl" style={{ width: 794 * scale, height: height * scale }}>
        <iframe
          ref={iframeRef}
          srcDoc={html}
          sandbox="allow-same-origin"
          onLoad={measureDocument}
          title="CV Preview"
          className="origin-top-left border-0 bg-white"
          style={{ width: 794, height, transform: `scale(${scale})` }}
        />
      </div>
    </div>
  );
}

export default function TailoredCVPreview({
  cv,
  design,
  versionId,
  translationVariantId,
  document_v2,
  language = "vi",
  onDownload,
}: {
  cv: TailoredCV;
  design: CVDesign;
  versionId?: string;
  translationVariantId?: string;
  document_v2?: CVDocumentV2 | null;
  language?: "vi" | "en";
  onDownload?: () => void;
}) {
  const [serverHtml, setServerHtml] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<CVRenderDiagnostics | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!versionId) {
      Promise.resolve().then(() => {
        setServerHtml(null);
      });
      return;
    }
    let isSubscribed = true;
    fetchTailoredCVPreviewAPI(versionId, translationVariantId)
      .then((res) => {
        if (isSubscribed) {
          setServerHtml(res.html);
          setDiagnostics(res.diagnostics);
          setErrorMsg(null);
        }
      })
      .catch((err) => {
        if (isSubscribed) {
          setErrorMsg(err?.message || "Không thể tải xem trước CV.");
        }
      });
    return () => {
      isSubscribed = false;
    };
  }, [versionId, design, translationVariantId]);

  const document = document_v2 || v1ToV2(cv.name, cv.headline, cv.contact_lines, cv.summary, cv.sections, cv.experience, cv.skills, cv.education);
  const fallbackHtml = useMemo(() => buildCVHtml(document, design, language), [document, design, language]);
  const activeHtml = versionId ? (errorMsg ? "" : (serverHtml || "")) : (serverHtml || fallbackHtml);
  const isLoading = !!versionId && !serverHtml && !errorMsg;

  const compactWillPaginate = design === "compact" && compactRenderingWarnings(document).length > 0;
  const isOutdated = document.requires_reprocessing
    || (document.reconstruction_version ?? 1) < CURRENT_RECONSTRUCTION_VERSION;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <p className="text-sm font-bold text-[#2F4F4F]">{CV_DESIGN_LABELS[design] || design}</p>
        {onDownload && (
          <button
            type="button"
            onClick={onDownload}
            className="rounded-xl bg-[#6A9B5E] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:bg-[#5a874e] active:scale-95"
          >
            Tải PDF
          </button>
        )}
      </div>
      {errorMsg && (
        <div role="alert" className="rounded-lg bg-red-100 border border-red-300 px-3 py-2 text-sm text-red-900 font-medium">
          {errorMsg}
        </div>
      )}
      {isOutdated && (
        <p role="status" className="rounded-lg bg-amber-100 border border-amber-300 px-3 py-2 text-sm text-amber-900 font-medium">
          Bản CV này được tạo bằng phiên bản trích xuất cũ (v2). Vui lòng tải lại tệp CV PDF để cập nhật cấu trúc mới nhất (v3).
        </p>
      )}
      {compactWillPaginate && (
        <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Nội dung được giữ nguyên và sẽ tiếp tục sang trang thứ hai.
        </p>
      )}
      {diagnostics?.warnings && diagnostics.warnings.length > 0 && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-sm text-blue-900">
          {diagnostics.warnings.join("; ")}
        </div>
      )}
      {isLoading ? (
        <div className="flex h-96 items-center justify-center rounded-2xl border border-dashed border-gray-200 bg-gray-50/50">
          <p className="text-sm font-medium text-gray-400">Đang tải bản xem trước...</p>
        </div>
      ) : activeHtml ? (
        <CVIframe html={activeHtml} />
      ) : (
        <div className="flex h-96 items-center justify-center rounded-2xl border border-dashed border-gray-200 bg-gray-50/50">
          <p className="text-sm font-medium text-gray-400">Không có bản xem trước</p>
        </div>
      )}
    </div>
  );
}
