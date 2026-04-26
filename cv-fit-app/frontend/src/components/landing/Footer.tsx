import Link from "next/link";
import Logo from "@/components/shared/Logo";

export default function Footer() {
  return (
    <footer
      className="max-w-7xl mx-auto space-y-8 md:space-y-12 text-[#5A6D6D] px-4 sm:px-6 lg:px-12 py-10 lg:py-16 border-t border-[#2F4F4F]/10"
    >
      {/* Industry Links Header */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="col-span-1 md:col-span-1">
          <Logo size="md" asLink={false} />
          <p className="mt-4 text-xs leading-relaxed max-w-[200px]">
            Công cụ AI hàng đầu Việt Nam giúp tối ưu CV và luyện phỏng vấn 1-1 chuyên nghiệp.
          </p>
        </div>
        
        <div className="space-y-4">
          <h4 className="text-[#2F4F4F] font-bold text-sm uppercase tracking-wider">Mẫu CV theo ngành</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/mau-cv/it-phan-mem" className="hover:text-[var(--primary)] transition-colors">IT & Phần mềm</Link></li>
            <li><Link href="/mau-cv/marketing" className="hover:text-[var(--primary)] transition-colors">Marketing & Truyền thông</Link></li>
            <li><Link href="/mau-cv/nhan-su-hr" className="hover:text-[var(--primary)] transition-colors">Hành chính Nhân sự</Link></li>
            <li><Link href="/mau-cv/tai-chinh-ngan-hang" className="hover:text-[var(--primary)] transition-colors">Tài chính Ngân hàng</Link></li>
          </ul>
        </div>

        <div className="space-y-4">
          <h4 className="text-[#2F4F4F] font-bold text-sm uppercase tracking-wider">Sản phẩm</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/app" className="hover:text-[var(--primary)] transition-colors">Phân tích CV</Link></li>
            <li><Link href="/interview" className="hover:text-[var(--primary)] transition-colors">Luyện phỏng vấn AI</Link></li>
            <li><Link href="#" className="hover:text-[var(--primary)] transition-colors">Hướng dẫn sử dụng</Link></li>
          </ul>
        </div>

        <div className="space-y-4">
          <h4 className="text-[#2F4F4F] font-bold text-sm uppercase tracking-wider">Công cụ</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="#" className="hover:text-[var(--primary)] transition-colors">Kiểm tra điểm ATS</Link></li>
            <li><Link href="#" className="hover:text-[var(--primary)] transition-colors">Dịch CV sang tiếng Anh</Link></li>
          </ul>
        </div>
      </div>

      <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-[rgba(47,79,79,0.05)] text-xs">
        <div>© 2026 Đậu — Chạm là Đậu. Được xây dựng vì sự nghiệp của người Việt.</div>
        <div className="flex gap-6 mt-4 md:mt-0">
          <Link href="#" className="hover:underline">Điều khoản</Link>
          <Link href="#" className="hover:underline">Bảo mật</Link>
        </div>
      </div>
    </footer>
  );
}
