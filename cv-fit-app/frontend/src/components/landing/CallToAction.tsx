import Link from "next/link";
import { ChevronRight } from "lucide-react";

export default function CallToAction() {
  return (
    <section className="max-w-7xl mx-auto text-center" style={{ padding: "8rem 3rem" }}>
      <h2
        className="font-heading font-bold leading-tight text-[#2F4F4F] mb-10"
        style={{ fontSize: "clamp(3rem,6vw,5rem)" }}
      >
        Sẵn sàng để ĐẬU?
      </h2>
      <p
        className="text-[#5A6D6D] leading-relaxed max-w-[800px] mx-auto mb-14"
        style={{ fontSize: "1.35rem" }}
      >
        Đừng để một bản CV cũ kỹ cản bước bạn. Hãy để Đậu giúp bạn tỏa sáng ngay hôm nay.
      </p>
      <Link href="/app" className="btn-green btn-green--lg">
        Bắt đầu ngay <ChevronRight size={24} />
      </Link>
    </section>
  );
}
