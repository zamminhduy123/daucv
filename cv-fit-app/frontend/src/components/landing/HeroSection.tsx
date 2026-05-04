import Link from "next/link";

import { ArrowRight, Play, CheckCircle2 } from "lucide-react";

export default function HeroSection() {
  return (
    <section 
      className="fade-up relative overflow-hidden pt-20 pb-24 lg:pt-16 lg:pb-24 bg-none lg:bg-[url('/bg.webp')] bg-cover bg-center bg-no-repeat"
    >
      <div className="max-w-7xl mx-auto px-6 relative z-10 flex flex-col items-center lg:items-start">
        {/* Content */}
        <div className="z-10 text-center lg:text-left lg:max-w-2xl">
          {/* Badge */}
          <div
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#2F4F4F] rounded-full border border-(--primary)/30 mb-6 lg:mb-8 text-left"
            style={{ padding: "0.5rem 1rem", backgroundColor: "rgba(152,193,142,0.15)" }}
          >
            <span className="text-(--primary) text-base shrink-0 mr-2 sm:mr-0">🌱</span>
            <span className="leading-tight sm:leading-normal">AI của người Việt, giúp bạn Đậu mọi vòng phỏng vấn</span>
          </div>

          {/* H1 */}
          <h1
            className="font-heading font-bold leading-tight text-[#2F4F4F] mb-4 lg:mb-6"
            style={{ letterSpacing: "-0.03em", fontSize: "clamp(2.5rem, 6vw, 4.5rem)" }}
          >
            Nâng cấp CV.<br />
            <span className="text-(--primary)">Chốt đơn sự nghiệp.</span>
          </h1>

          {/* Subtitle */}
          <p
            className="text-[#5A6D6D] leading-relaxed mb-8 lg:mb-10 mx-auto lg:mx-0 text-base lg:text-xl"
            style={{ maxWidth: "600px" }}
          >
            <strong className="font-semibold text-[#2F4F4F]">Đậu (daucv.com)</strong> là công cụ AI số 1 tại Việt Nam giúp ứng viên sửa CV chuẩn ATS và luyện phỏng vấn 1-1 sát với Job Description nhất.
          </p>

          {/* CTA */}
          <div className="flex flex-col sm:flex-row gap-4 items-center justify-center lg:justify-start mb-6">
            <Link href="/app" className="w-full sm:w-auto group px-6 py-4 lg:px-8 bg-(--primary) text-white rounded-xl font-bold hover:opacity-90 transition-all shadow-md flex justify-center items-center gap-2 text-base lg:text-lg">
              Phân tích CV/JD <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link 
              href="/app" 
              className="w-full sm:w-auto inline-flex items-center justify-center gap-3 px-6 py-4 lg:px-8 rounded-xl font-bold bg-white text-[#2F4F4F] border border-gray-200 hover:shadow-md transition-all text-base lg:text-lg"
            >
              <div className="bg-gray-100 rounded-full p-1"><Play size={16} fill="currentColor" /></div>
              Phỏng vấn thử
            </Link>
          </div>

          {/* Bullet Points */}
          <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 sm:gap-6 text-sm text-[#5A6D6D] font-medium">
            <span className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-(--primary)" /> Hoàn toàn miễn phí
            </span>
            <span className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-(--primary)" /> Không lưu trữ dữ liệu người dùng
            </span>
          </div>
        </div>

        {/* Right Column - Image */}
        {/* <div className="relative w-1/2 h-full">
        </div> */}
      </div>
    </section>
  );
}
