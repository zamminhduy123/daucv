import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";
import { nganhNgheList } from "@/app/mau-cv/[nganh-nghe]/page";

const INDUSTRY_ICONS: Record<string, string> = {
  "it-phan-mem": "💻",
  "marketing": "📢",
  "nhan-su-hr": "🤝",
};

export default function TemplatesPage() {
  const industries = Object.entries(nganhNgheList);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <h1 className="font-heading font-bold text-3xl text-[#2F4F4F] mb-2">
          Thư viện Mẫu CV
        </h1>
        <p className="text-gray-500 text-sm">
          Chọn ngành nghề để xem mẫu CV chuẩn ATS được tối ưu bởi Bé Đậu.
        </p>
      </div>

      {/* Industry Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mb-12">
        {industries.map(([slug, data]) => (
          <Link
            key={slug}
            href={`/app/templates/${slug}`}
            className="group bg-white border border-gray-100 rounded-2xl p-6 hover:shadow-md hover:border-[var(--primary)]/30 transition-all duration-200 no-underline flex flex-col"
          >
            <div className="text-3xl mb-4">{INDUSTRY_ICONS[slug] ?? "📄"}</div>
            <h2 className="font-heading font-bold text-[#2F4F4F] text-lg mb-2 group-hover:text-[var(--primary)] transition-colors">
              {data.name}
            </h2>
            <p className="text-xs text-gray-500 leading-relaxed flex-1 mb-4 line-clamp-2">
              {data.subtitle}
            </p>
            <div className="flex flex-wrap gap-1.5 mb-4">
              {data.keywords.slice(0, 3).map((kw) => (
                <span
                  key={kw}
                  className="text-[10px] font-medium bg-[var(--primary)]/10 text-[var(--primary)] px-2 py-0.5 rounded-full"
                >
                  {kw}
                </span>
              ))}
              {data.keywords.length > 3 && (
                <span className="text-[10px] font-medium bg-gray-100 text-gray-400 px-2 py-0.5 rounded-full">
                  +{data.keywords.length - 3}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[var(--primary)] text-xs font-semibold mt-auto">
              Xem mẫu CV
              <ArrowRight size={13} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>
        ))}

        {/* Coming soon placeholder */}
        <div className="bg-gray-50 border border-dashed border-gray-200 rounded-2xl p-6 flex flex-col items-center justify-center text-center min-h-[220px]">
          <FileText size={28} className="text-gray-300 mb-3" />
          <p className="text-sm font-medium text-gray-400">Thêm ngành nghề</p>
          <p className="text-xs text-gray-300 mt-1">Sắp ra mắt 🌱</p>
        </div>
      </div>
    </div>
  );
}
