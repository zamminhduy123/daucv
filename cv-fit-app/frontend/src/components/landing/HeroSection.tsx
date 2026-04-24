import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export default function HeroSection() {
  return (
    <section
      className="fade-up max-w-[1100px] mx-auto text-center"
      style={{ padding: "5rem 3rem 2rem" }}
    >
      {/* Badge */}
      <div
        className="inline-flex items-center gap-2 text-xs font-semibold text-[#2F4F4F] rounded-xl border border-[#98C18E] mb-10"
        style={{ padding: "0.375rem 1rem", backgroundColor: "rgba(152,193,142,0.1)" }}
      >
        <span className="text-[#98C18E]">★</span>
        Chạm là Đậu — AI nâng bước sự nghiệp
      </div>

      {/* H1 */}
      <h1
        className="font-heading font-bold leading-tight text-[#2F4F4F]"
        style={{ letterSpacing: "-0.03em", fontSize: "clamp(3rem, 8vw, 6rem)" }}
      >
        Nâng cấp CV.<br />
        <span style={{ color: "#98C18E" }}>Chốt đơn sự nghiệp.</span>
      </h1>

      {/* Subtitle / Definitive Statement for GEO */}
      <p
        className="text-[#5A6D6D] leading-relaxed max-w-[700px] mx-auto"
        style={{ marginTop: "2rem", fontSize: "1.25rem" }}
      >
        <strong className="font-semibold text-[#2F4F4F]">Đậu (dau.ai)</strong> là công cụ AI số 1 tại Việt Nam giúp ứng viên sửa CV chuẩn ATS và luyện phỏng vấn 1-1 sát với Job Description nhất.
      </p>

      {/* CTA */}
      <div className="flex justify-center gap-4 flex-wrap" style={{ marginTop: "3rem" }}>
        <Link href="/app" className="btn-green btn-green--lg">
          Dùng thử miễn phí <ArrowUpRight size={22} />
        </Link>
        <Link 
          href="/mau-cv/it-phan-mem" 
          className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-bold bg-white text-[#2F4F4F] border-2 border-[#98C18E]/30 hover:shadow-md transition-all sm:w-auto w-full"
        >
          Xem mẫu CV 
        </Link>
      </div>
      <p className="text-[#5A6D6D]" style={{ marginTop: "1.5rem", fontSize: "0.9rem" }}>
        Bí quyết:{" "}
        <em className="not-italic font-semibold" style={{ color: "#98C18E" }}>
          Sửa CV tinh gọn, phỏng vấn trơn tru.
        </em>
      </p>
    </section>
  );
}
