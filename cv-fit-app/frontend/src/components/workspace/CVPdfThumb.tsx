"use client";

import { useEffect, useRef, useState } from "react";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";

let workerConfigured = false;

function ensurePdfWorker() {
  if (!workerConfigured && typeof window !== "undefined") {
    GlobalWorkerOptions.workerSrc = new URL(
      "pdfjs-dist/build/pdf.worker.min.mjs",
      import.meta.url,
    ).toString();
    workerConfigured = true;
  }
}

interface CVPdfThumbProps {
  url: string;
  label: string;
  onError: () => void;
}

/** Renders the first PDF page onto a canvas thumbnail. Any failure
 * (expired signed URL, CORS, corrupt file) reports via onError so the
 * caller can fall back to the text preview. */
export default function CVPdfThumb({ url, label, onError }: CVPdfThumbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) setLoading(true);
    });
    ensurePdfWorker();

    const loadingTask = getDocument({ url });
    loadingTask.promise
      .then(async (doc) => {
        if (cancelled) return;
        const page = await doc.getPage(1);
        if (cancelled) return;
        const canvas = canvasRef.current;
        if (!canvas) {
          if (!cancelled) onError();
          return;
        }
        const targetWidth = 720;
        const viewport = page.getViewport({ scale: 1 });
        const scaled = page.getViewport({ scale: targetWidth / viewport.width });
        canvas.width = Math.floor(scaled.width);
        canvas.height = Math.floor(scaled.height);
        await page.render({ canvas, viewport: scaled, background: "#ffffff" }).promise;
        if (!cancelled) setLoading(false);
      })
      .catch(() => {
        if (!cancelled) onError();
      });

    return () => {
      cancelled = true;
      loadingTask.destroy().catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return (
    <div className="relative aspect-[210/297] overflow-hidden bg-[#FDFDFB]">
      {loading && <div className="absolute inset-0 animate-pulse bg-gray-100" />}
      <canvas ref={canvasRef} aria-label={label} className="h-full w-full object-contain" />
    </div>
  );
}
