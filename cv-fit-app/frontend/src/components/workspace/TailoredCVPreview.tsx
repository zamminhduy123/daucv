"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { CV_DESIGN_LABELS } from "@/lib/cv-designs";
import { buildCVHtml, compactRenderingWarnings } from "@/lib/cv-render-html";
import { v1ToV2 } from "@/lib/cv-v1-to-v2-adapter";
import type { CVDesign, CVDocumentV2, TailoredCV } from "@/types";

function CVIframe({ doc, design, language }: { doc: CVDocumentV2; design: CVDesign; language: "vi" | "en" }) {
  const sensorRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [scale, setScale] = useState(1);
  const [height, setHeight] = useState(1123);
  const html = useMemo(() => buildCVHtml(doc, design, language), [doc, design, language]);

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

  return <div className="relative flex w-full justify-center">
    <div ref={sensorRef} className="pointer-events-none invisible absolute inset-x-0" />
    <div className="overflow-hidden rounded-sm bg-white shadow-xl" style={{ width: 794 * scale, height: height * scale }}>
      <iframe ref={iframeRef} srcDoc={html} onLoad={measureDocument} title="CV Preview" className="origin-top-left border-0 bg-white" style={{ width: 794, height, transform: `scale(${scale})` }} />
    </div>
  </div>;
}

export default function TailoredCVPreview({ cv, design, document_v2, language = "vi", onDownload }: {
  cv: TailoredCV;
  design: CVDesign;
  document_v2?: CVDocumentV2 | null;
  language?: "vi" | "en";
  onDownload?: () => void;
}) {
  const document = document_v2 || v1ToV2(cv.name, cv.headline, cv.contact_lines, cv.summary, cv.sections, cv.experience, cv.skills, cv.education);
  const compactWillPaginate = design === "compact_one_page" && compactRenderingWarnings(document).length > 0;
  return <div className="space-y-4">
    <div className="flex items-center justify-between print:hidden">
      <p className="text-sm font-bold text-[#2F4F4F]">{CV_DESIGN_LABELS[design]}</p>
      {onDownload && <button type="button" onClick={onDownload} className="rounded-xl bg-[#6A9B5E] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:bg-[#5a874e] active:scale-95">Tải PDF</button>}
    </div>
    {compactWillPaginate && <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">Nội dung được giữ nguyên và sẽ tiếp tục sang trang thứ hai.</p>}
    <CVIframe doc={document} design={design} language={language} />
  </div>;
}
