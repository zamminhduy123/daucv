import Link from "next/link";
import { ChevronRight } from "lucide-react";
import Logo from "@/components/shared/Logo";

export default function CtaAndFooter() {
  return (
    <>
      {/* FINAL CTA */}
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

      {/* FOOTER */}
      <footer
        className="max-w-7xl mx-auto flex items-center justify-between text-sm text-[#5A6D6D]"
        style={{ padding: "3rem", borderTop: "1px solid rgba(47,79,79,0.1)" }}
      >
        <Logo size="md" asLink={false} />
        <div>© 2026 Đậu — Chạm là Đậu. Được xây dựng vì sự nghiệp của người Việt.</div>
      </footer>
    </>
  );
}
