"use client";

import { useWorkspace } from "@/context/WorkspaceContext";
import { RefreshCw, ShieldCheck, Sprout } from "lucide-react";

interface DauOverloadScreenProps {
  message: string;
  onRetry: () => void;
}

function DauMascot() {
  return (
    <img src="/tired.webp" alt="Đậu, chú đậu xanh đang hơi mệt nhưng vẫn vui vẻ" className="h-[120px] w-[120px]" />
  );
}

export function DauOverloadScreen({ message, onRetry }: DauOverloadScreenProps) {
  const { setFeedbackOpen } = useWorkspace();
  return (
    <section className="relative isolate flex min-h-[calc(100vh-10rem)] items-center justify-center overflow-hidden px-4 py-8 text-[#2F4F4F] sm:px-6 sm:py-10">
      <div className="relative z-10 flex w-full max-w-lg flex-col items-center">
        <article className="w-full rounded-3xl border-t-4 border-t-[#6A9B5E] bg-white p-7 text-center shadow-md">
          <div className="mx-auto flex h-[140px] w-[140px] flex-col items-center justify-center rounded-2xl">
            <DauMascot />
          </div>
          <h1 className="mt-4 text-xl font-bold leading-tight text-[#2F4F4F]">Đậu hơi ngộp xíu, cho Đậu thở tí nha! 🫘💨</h1>
          <p className="mt-2 text-sm leading-relaxed text-[#2F4F4F]/75">{message}</p>
          <div className="mt-4 rounded-2xl border border-green-100 bg-green-50 p-3 text-left">
            <p className="text-sm leading-relaxed text-[#2F4F4F]/80"><Sprout aria-hidden="true" size={18} className="mr-1.5 inline-block -translate-y-0.5 text-green-600" />Đậu vẫn đang trong giai đoạn lớn lên 🌱 nên thỉnh thoảng hơi trục trặc là chuyện bình thường. Nếu trải nghiệm chưa tốt, ghé mục Góp ý kể Đậu nghe nha — Đậu sẽ cải thiện dần.</p>
            <p className="mt-2 text-sm font-medium leading-relaxed text-green-700"><ShieldCheck aria-hidden="true" size={18} className="mr-1.5 inline-block -translate-y-0.5" />Yên tâm là credit sẽ không bị trừ nếu hệ thống xử lý không thành công đâu, bạn cứ thử lại thoải mái.</p>
          </div>
          <button type="button" onClick={onRetry} className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-[#6A9B5E] px-8 py-2.5 text-base font-semibold text-white transition-colors hover:bg-[#85AE7B] focus:outline-none focus:ring-2 focus:ring-[#6A9B5E] focus:ring-offset-2" aria-label="Thử lại xử lý CV">
            <RefreshCw aria-hidden="true" size={16} />
            <span>Thử lại</span>
          </button>
          <button onClick={() => setFeedbackOpen(true)} className="mt-2 inline-block text-sm text-[#6A9B5E] underline-offset-2 hover:underline">Góp ý cho Đậu</button>
        </article>
      </div>
    </section>
  );
}
