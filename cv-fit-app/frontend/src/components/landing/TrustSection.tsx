import { CheckCircle2 } from "lucide-react";

export default function TrustSection() {
  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-8">
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8 text-sm text-[#5A6D6D] font-medium">
        <span className="flex items-center gap-2">
          <CheckCircle2 size={16} className="text-[var(--primary)]" /> Hoàn toàn miễn phí
        </span>
        <span className="flex items-center gap-2">
          <CheckCircle2 size={16} className="text-[var(--primary)]" /> Không lưu trữ dữ liệu người dùng
        </span>
      </div>
    </section>
  );
}
