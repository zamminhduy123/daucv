import Image from "next/image";
import { Coffee } from "lucide-react";

interface SupportCardProps {
  compact?: boolean;
  mini?: boolean;
}

export default function SupportCard({ compact = false, mini = false }: SupportCardProps) {
  const isCompactMode = compact || mini;

  const wrapperClass = mini
    ? "relative overflow-hidden rounded-xl border border-[#D9DFC8] bg-[#F1F2E9] px-3 py-2.5 sm:px-4 sm:py-3 shadow-sm"
    : compact
      ? "relative overflow-hidden rounded-2xl border border-[#D9DFC8] bg-[#F1F2E9] px-4 py-4 sm:px-5 sm:py-4 shadow-[0_8px_24px_rgba(47,79,79,0.12)]"
      : "relative overflow-hidden rounded-3xl border border-[#D9DFC8] bg-[#F1F2E9] px-5 py-5 sm:px-8 sm:py-7 shadow-[0_10px_30px_rgba(47,79,79,0.08)]";

  const titleClass = mini
    ? "text-sm sm:text-base font-bold text-[#1F2E2E] tracking-tight"
    : compact
      ? "text-lg sm:text-xl font-bold text-[#1F2E2E] tracking-tight"
      : "text-2xl sm:text-4xl font-bold text-[#1F2E2E] tracking-tight";

  const descriptionClass = mini
    ? "mt-1 text-xs leading-snug text-[#2F4F4F]/90"
    : compact
      ? "mt-2 text-sm sm:text-base leading-relaxed text-[#2F4F4F]/90"
      : "mt-3 text-base sm:text-[1.9rem] leading-relaxed text-[#2F4F4F]/90";

  const buttonClass = mini
    ? "mt-2 inline-flex items-center gap-1.5 rounded-lg bg-linear-to-r from-[#C62B22] to-[#B22222] px-3 py-1.5 text-xs font-semibold text-white shadow transition-transform duration-300 hover:scale-[1.02]"
    : compact
      ? "mt-4 inline-flex items-center gap-2 rounded-xl bg-linear-to-r from-[#C62B22] to-[#B22222] px-4 py-2.5 text-sm sm:text-base font-semibold text-white shadow-lg transition-transform duration-300 hover:scale-[1.03]"
      : "mt-6 inline-flex items-center gap-2 rounded-2xl bg-linear-to-r from-[#C62B22] to-[#B22222] px-7 py-3.5 text-base sm:text-lg font-semibold text-white shadow-lg transition-transform duration-300 hover:scale-[1.03]";

  return (
    <div className={wrapperClass}>
      <div className={`grid items-center ${mini ? "grid-cols-[1fr_auto] gap-2.5" : compact ? "grid-cols-1 gap-3 md:grid-cols-[1.3fr_0.7fr]" : "grid-cols-1 gap-6 md:grid-cols-[1.15fr_0.85fr]"}`}>
        <div className="text-left">
          <h3 className={titleClass}>
            Tiếp thêm may mắn cho Đậu?
          </h3>
          <p className={descriptionClass}>
            {mini
              ? "Bé Đậu vừa đồng hành xong câu đầu tiên cùng bạn — nếu thấy hữu ích, mời Đậu một bát chè đỏ nhé!"
              : "Bé Đậu đã nỗ lực hết mình để giúp bạn có một CV “nét”. Nếu bạn thấy hữu ích, hãy tặng Admin một bát Chè Đậu Đỏ để giữ lấy may mắn cho vòng phỏng vấn sắp tới nhé!"}
          </p>

          <button className={buttonClass}>
            <Coffee className={mini ? "h-4 w-4" : "h-5 w-5"} />
            Tặng Chè Đậu Đỏ (20k) 🍵
          </button>
        </div>

        <div className={`relative mx-auto ${mini ? "w-16 sm:w-20" : `w-full ${isCompactMode ? "max-w-56 md:max-w-72" : "max-w-90 md:max-w-120"}`}`}>
          <Image
            src="/redbean.webp"
            alt="Bé Đậu và bát chè đậu đỏ"
            width={900}
            height={600}
            priority={false}
            className="h-auto w-full object-contain"
          />
        </div>
      </div>
    </div>
  );
}
