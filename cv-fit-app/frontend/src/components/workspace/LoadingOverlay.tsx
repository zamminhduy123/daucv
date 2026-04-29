"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

const MESSAGES = [
  "Bé Đậu đang đọc JD của bạn...",
  "Đối chiếu kỹ năng...",
  "Tinh chỉnh từng câu chữ...",
  "Sắp xong rồi ✨",
];

export default function LoadingOverlay({messages = MESSAGES} : {messages?: string[]}) {
  const [dots, setDots] = useState(0);
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    const d = setInterval(() => setDots((v) => (v + 1) % 4), 450);
    const m = setInterval(() => setMsgIdx((i) => Math.min(i + 1, MESSAGES.length - 1)), 500);
    return () => { clearInterval(d); clearInterval(m); };
  }, []);

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
            className="drop-shadow-md"
          />
        </div>

        <h3 className="font-heading font-bold text-[#2F4F4F] text-2xl mb-3">
          Bé Đậu đang làm việc{".".repeat(dots)}
        </h3>
        <p className="text-[#5A6D6D] text-base leading-relaxed min-h-[1.6rem]">
          {MESSAGES[msgIdx]}
        </p>

        {/* Progress bar */}
        <div
          className="mt-8 rounded-full overflow-hidden h-1.5"
          style={{ backgroundColor: "rgba(152,193,142,0.2)" }}
        >
          <div
            className="h-full rounded-full bg-(--primary)"
            style={{ animation: "loading-bar 2s ease-in-out forwards" }}
          />
        </div>
      </div>
    </div>
  );
}
