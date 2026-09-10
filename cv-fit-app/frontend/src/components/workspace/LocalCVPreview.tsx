"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Eye, FileText, Maximize2, Minimize2 } from "lucide-react";
import { buildCVHtml, compactRenderingWarnings, type CVTypographyConfig } from "@/lib/cv-render-html";
import type { CVDesign, CVDocumentV2 } from "@/types";

/**
 * Reusable iframe renderer. Exposes clean paper page view.
 */
export function CVIframe({
  html,
  iframeRef: externalRef,
  onHeightChange,
  onPageCountChange,
  scrollContainerRef,
}: {
  html: string;
  iframeRef?: React.RefObject<HTMLIFrameElement | null>;
  onHeightChange?: (h: number) => void;
  onPageCountChange?: (count: number) => void;
  scrollContainerRef?: React.RefObject<HTMLDivElement | null>;
}) {
  const sensorRef = useRef<HTMLDivElement>(null);
  const internalRef = useRef<HTMLIFrameElement>(null);
  const iframeRef = externalRef ?? internalRef;
  const [scale, setScale] = useState(1);
  const [height, setHeight] = useState(1123);

  useLayoutEffect(() => {
    const sensor = sensorRef.current;
    if (!sensor) return;
    const resize = () => {
      const containerWidth = sensor.clientWidth;
      if (containerWidth > 0) {
        // Fit the 794px A4 CV completely into the preview container
        const targetWidth = Math.max(280, containerWidth - 16);
        setScale(targetWidth / 794);
      }
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(sensor);
    return () => observer.disconnect();
  }, []);

  const measureDocument = () => {
    const check = () => {
      const doc = iframeRef.current?.contentDocument;
      const win = iframeRef.current?.contentWindow as
        | (Window & { applyPageBreaks?: () => void })
        | null;
      win?.applyPageBreaks?.();
      const body = doc?.body;
      const article = doc?.querySelector("article");
      if (body && article) {
        const breaks = doc.querySelectorAll(".cv-page-break-container");
        const calculatedPages =
          breaks.length > 0 ? breaks.length + 1 : Math.max(1, Math.ceil(body.scrollHeight / 1123));
        const newHeight = Math.max(1123, (article as HTMLElement).offsetHeight);
        setHeight(newHeight);
        onHeightChange?.(newHeight);
        onPageCountChange?.(calculatedPages);
      }
    };
    check();
    requestAnimationFrame(check);
    setTimeout(check, 80);
    setTimeout(check, 250);
  };

  return (
    <div ref={scrollContainerRef} className="relative flex w-full flex-col items-center bg-transparent">
      <div ref={sensorRef} className="pointer-events-none invisible absolute inset-x-0 top-0 h-0" />
      <div
        className="overflow-hidden bg-white rounded-xl border border-slate-200/70 shadow-[0_4px_20px_rgba(45,122,88,0.08)]"
        style={{ width: 794 * scale, height: height * scale }}
      >
        <iframe
          ref={iframeRef}
          srcDoc={html}
          sandbox="allow-scripts allow-same-origin"
          scrolling="no"
          onLoad={measureDocument}
          title="CV Preview"
          className="origin-top-left border-0 bg-white block"
          style={{ width: 794, height, transform: `scale(${scale})`, overflow: "hidden" }}
        />
      </div>
    </div>
  );
}

/**
 * Scroll the iframe to the requested section.
 */
export function scrollIframeToSection(
  iframe: HTMLIFrameElement | null,
  sectionType: string,
): boolean {
  if (!iframe?.contentWindow) return false;
  const doc = iframe.contentDocument;
  if (!doc) return false;
  const el = doc.querySelector(`section[data-section-type="${CSS.escape(sectionType)}"]`);
  if (el) {
    const top = (el as HTMLElement).offsetTop;
    iframe.contentWindow.scrollTo({ top, behavior: "smooth" });
    return true;
  }
  return false;
}

interface LocalPreviewProps {
  document: CVDocumentV2;
  design: CVDesign;
  language?: "vi" | "en";
  activeSectionType?: string | null;
  iframeRef?: React.RefObject<HTMLIFrameElement | null>;
  typography?: CVTypographyConfig;
}

export default function LocalCVPreview({
  document,
  design,
  language = "vi",
  activeSectionType,
  iframeRef: externalIframeRef,
  typography,
}: LocalPreviewProps) {
  const [, setDocHeight] = useState(1123);
  const [pageCount, setPageCount] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const html = useMemo(
    () => buildCVHtml(document, design, language, typography),
    [document, design, language, typography],
  );

  const compactWillPaginate = design === "compact" && compactRenderingWarnings(document).length > 0;
  const internalIframeRef = useRef<HTMLIFrameElement>(null);
  const iframeRef = externalIframeRef ?? internalIframeRef;

  // Listen for page count messages posted from the iframe's pagination script
  useEffect(() => {
    const handleMsg = (e: MessageEvent) => {
      if (e.data?.type === "CV_PAGE_COUNT" && typeof e.data.count === "number") {
        setPageCount(Math.max(1, e.data.count));
      }
    };
    window.addEventListener("message", handleMsg);
    return () => window.removeEventListener("message", handleMsg);
  }, []);

  // After the iframe reloads for a new document, jump to the active section.
  useEffect(() => {
    if (!activeSectionType) return;
    const id = requestAnimationFrame(() => {
      scrollIframeToSection(iframeRef.current, activeSectionType);
    });
    return () => cancelAnimationFrame(id);
  }, [html, activeSectionType, iframeRef]);

  const content = (
    <div
      className={`flex flex-col ${
        isFullscreen
          ? "fixed inset-0 z-50 bg-[#EEF2EE] p-4"
          : "h-full bg-[#EEF2EE] overflow-hidden"
      }`}
    >
      {/* Viewer Header */}
      <div className="flex items-center justify-between px-5 py-3 shrink-0">
        <div className="flex items-center gap-2.5">
          <Eye size={16} className="text-[#2D7A58]" />
          <span className="text-sm font-bold text-slate-800">Xem trước</span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#EAF5EC] px-2.5 py-0.5 text-xs font-semibold text-[#2D7A58] border border-[#6A9B5E]/25">
            <FileText size={12} />
            {pageCount} trang
          </span>
          {compactWillPaginate && (
            <span className="text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full">
              Sẽ chuyển 2 trang khi in PDF
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setIsFullscreen((v) => !v)}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-slate-700 transition-colors cursor-pointer"
          title={isFullscreen ? "Thu nhỏ" : "Phóng to toàn màn hình"}
          aria-label={isFullscreen ? "Thu nhỏ" : "Phóng to toàn màn hình"}
        >
          {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>
      </div>

      {/* Viewer Paper Canvas Area */}
      <div className="flex-1 min-h-0 overflow-y-auto bg-[#EEF2EE] flex justify-center items-start">
        <CVIframe
          html={html}
          iframeRef={iframeRef}
          onHeightChange={(h) => setDocHeight(h)}
          onPageCountChange={(cnt) => setPageCount(cnt)}
          scrollContainerRef={scrollContainerRef}
        />
      </div>
    </div>
  );

  return content;
}