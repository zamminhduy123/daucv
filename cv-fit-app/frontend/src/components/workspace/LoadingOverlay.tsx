"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

interface LoadingOverlayProps {
  message?: string;
  messages?: string[];
  retryAttempt?: number;
  retryTotal?: number;
  onCancel?: () => void;
}

export default function LoadingOverlay({
  message,
  messages,
  retryAttempt,
  retryTotal,
  onCancel,
}: LoadingOverlayProps) {
  const [dots, setDots] = useState(0);
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const d = setInterval(() => setDots((v) => (v + 1) % 4), 450);
    const m = !message && messages?.length
      ? setInterval(
          () => setMessageIndex((index) => Math.min(index + 1, messages.length - 1)),
          1500,
        )
      : null;
    return () => {
      clearInterval(d);
      if (m) clearInterval(m);
    };
  }, [message, messages]);

  const displayMessage = message ?? messages?.[messageIndex] ?? "Đang xử lý...";

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-100"
      style={{ backgroundColor: "rgba(47,79,79,0.55)", backdropFilter: "blur(6px)" }}
    >
      <div
        className="bg-[#F9F9F2] text-center rounded-[28px] shadow-2xl max-w-sm w-[90%]"
        style={{ padding: "3.5rem 4rem" }}
      >
        {/* Bouncing sprout -> Mascot Image */}
        <div className="mb-6 inline-block" style={{ animation: "bounce 0.8s ease-in-out infinite" }}>
          <Image 
            src="/main-icon.webp" 
            alt="Đang xử lý..." 
            width={80} 
            height={80} 
            style={{ width: "auto", height: "auto" }}
            className="drop-shadow-md"
          />
        </div>

        <h3 className="font-heading font-bold text-[#2F4F4F] text-2xl mb-3">
          Bé Đậu đang làm việc{".".repeat(dots)}
        </h3>
        <p className="text-[#5A6D6D] text-base leading-relaxed min-h-[1.6rem]">
          {displayMessage}
        </p>
        {retryAttempt && retryTotal ? (
          <p className="mt-2 text-xs font-semibold text-amber-700">
            Lần thử {retryAttempt}/{retryTotal}
          </p>
        ) : null}

        {/* Progress bar */}
        <div
          className="mt-8 rounded-full overflow-hidden h-1.5"
          style={{ backgroundColor: "rgba(152,193,142,0.2)" }}
        >
          <div
            className="h-full rounded-full bg-(--primary)"
            style={{ animation: "loading-bar 2s ease-in-out infinite" }}
          />
        </div>
        {onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="mt-6 text-sm font-semibold text-[#5A6D6D] underline-offset-4 hover:text-[#B22222] hover:underline"
          >
            Hủy phân tích
          </button>
        ) : null}
      </div>
    </div>
  );
}
