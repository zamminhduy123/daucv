import Link from "next/link";
import { ChevronRight } from "lucide-react";

export default function CallToAction() {
  return (
    <section className="max-w-7xl mx-auto text-center px-4 sm:px-6 lg:px-12 py-20 lg:py-32">
      <h2
        className="font-heading font-bold leading-tight text-[#2F4F4F] mb-6 md:mb-10"
        style={{ fontSize: "clamp(2.5rem,6vw,5rem)" }}
      >
        Sẵn sàng để ĐẬU?
      </h2>
      <p
        className="text-[#5A6D6D] leading-relaxed max-w-[800px] mx-auto mb-10 md:mb-14 text-base md:text-xl px-4"
      >
        Đừng để một bản CV cũ kỹ cản bước bạn. Hãy để Đậu giúp bạn tỏa sáng ngay hôm nay.
      </p>
      <Link href="/app" className="btn-green btn-green--lg">
        Bắt đầu ngay <ChevronRight size={24} />
      </Link>
    </section>
  );
}
