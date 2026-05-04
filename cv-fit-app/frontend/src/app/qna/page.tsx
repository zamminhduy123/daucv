import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import {
  MessageCircle,
  Sparkles,
  Shield,
  Zap,
  TrendingUp,
  FileText,
  Search,
  Languages,
  Mic,
  ChevronDown,
  Leaf,
  ChevronRight,
} from "lucide-react";
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "@/components/landing/Footer";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

/* ─────────────────────────────────────────────
   SEO Metadata
───────────────────────────────────────────── */
export const metadata: Metadata = {
  title: "Hỏi Đáp & Cẩm Nang CV — Đậu (daucv.com)",
  description:
    "Mọi thắc mắc của bạn về ATS, CV chuẩn, phỏng vấn và hành trình tìm việc đều được giải đáp tại đây. Cẩm nang CV chuẩn ATS từ Đậu.",
  openGraph: {
    title: "Trạm Hỏi Đáp & Cẩm Nang CV — Đậu (daucv.com)",
    description:
      "Giải đáp mọi thắc mắc về CV, ATS, phỏng vấn và hành trình tìm việc.",
    url: "https://daucv.com/qna",
    type: "website",
    locale: "vi_VN",
  },
};

/* ─────────────────────────────────────────────
   FAQ Data — with icon + summary per item
───────────────────────────────────────────── */
const faqItems = [
  {
    icon: FileText,
    question: "Có nên dùng chung 1 CV để rải cho nhiều công ty không?",
    answer:
      "Không nên. Hơn 70% doanh nghiệp hiện nay dùng hệ thống ATS để quét từ khóa. Việc dùng chung 1 CV sẽ khiến bạn dễ bị loại ngay từ vòng đầu vì không khớp từ khóa của từng JD cụ thể. Hãy dùng Bé Đậu để tinh chỉnh CV khớp 100% với từng JD chỉ trong vài giây.",
    summary:
      "Mỗi JD cần một CV riêng. Dùng Đậu để tinh chỉnh nhanh — không cần viết lại từ đầu.",
  },
  {
    icon: Search,
    question: "CV chuẩn ATS là gì và làm sao để kiểm tra?",
    answer:
      "CV chuẩn ATS là CV được thiết kế tối giản, không dùng bảng biểu phức tạp, cột nhiều tầng, đồ họa hay hình ảnh che khuất chữ. Hệ thống ATS cần đọc được văn bản thuần. Bạn có thể tải CV lên Daucv.com để AI chấm điểm \"Chuẩn ATS\" miễn phí — kết quả trả về ngay lập tức.",
    summary:
      "CV chuẩn ATS = tối giản, text-based. Kiểm tra ngay tại Daucv.com, miễn phí.",
  },
  {
    icon: Shield,
    question: "Tại sao CV của tôi hay bị loại ở vòng gửi hồ sơ?",
    answer:
      "Thường do hai nguyên nhân chính: (1) thiếu từ khóa chuyên môn mà nhà tuyển dụng tìm kiếm, hoặc (2) viết kinh nghiệm chung chung, không có số liệu định lượng. Đậu sẽ phân tích CV của bạn so với JD, phát hiện từ khóa thiếu và gợi ý cách viết lại theo chuẩn thực chiến.",
    summary:
      "Thiếu từ khóa + thiếu số liệu = bị loại sớm. Đậu giúp bạn vá đúng chỗ.",
  },
  {
    icon: Languages,
    question: "Nên viết CV bằng tiếng Anh hay tiếng Việt?",
    answer:
      "Nguyên tắc vàng: JD viết bằng tiếng nào, CV nộp bằng tiếng đó. Nếu JD song ngữ, ưu tiên tiếng Anh để thể hiện năng lực. Daucv.com hỗ trợ phân tích và tối ưu CV bằng cả tiếng Anh và tiếng Việt với độ chính xác như nhau.",
    summary:
      "JD tiếng nào, CV tiếng đó. Đậu hỗ trợ cả Anh lẫn Việt.",
  },
  {
    icon: Mic,
    question: "Làm sao để hết run khi phỏng vấn?",
    answer:
      "Cách duy nhất là luyện tập thực tế, lặp đi lặp lại. Tính năng \"Phỏng vấn 1-1\" của Đậu cho phép bạn thực hành trả lời bằng giọng nói theo câu hỏi sát với JD thực tế, sau đó nhận phân tích chi tiết về nội dung, ngôn ngữ và độ tự tin ngay lập tức.",
    summary:
      "Luyện thật nhiều trước khi chiến. Đậu là người phỏng vấn thử không phán xét bạn.",
  },
];

/* ─────────────────────────────────────────────
   Feature Bar Items
───────────────────────────────────────────── */
const featureBarItems = [
  {
    icon: Sparkles,
    title: "AI Phân tích",
    subtitle: "Chính xác & Nhanh chóng",
  },
  {
    icon: Shield,
    title: "Bảo mật 100%",
    subtitle: "Không lưu trữ dữ liệu",
  },
  {
    icon: Zap,
    title: "Gợi ý thực chiến",
    subtitle: "Rõ ràng, dễ áp dụng",
  },
  {
    icon: TrendingUp,
    title: "Tăng tỷ lệ Đậu",
    subtitle: "Nhận nhiều lời mời hơn",
  },
];

/* ─────────────────────────────────────────────
   JSON-LD Structured Data (FAQPage)
───────────────────────────────────────────── */
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqItems.map((f) => ({
    "@type": "Question",
    name: f.question,
    acceptedAnswer: { "@type": "Answer", text: f.answer },
  })),
};

/* ═══════════════════════════════════════════
   PAGE COMPONENT
═══════════════════════════════════════════ */
export default function QnAPage() {
  return (
    <main className="min-h-screen bg-white text-[#2F4F4F]">
      {/* Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <LandingNavbar />

      {/* ══════════════════════════════════════
          1. HERO SECTION
      ══════════════════════════════════════ */}
      <section className="max-w-7xl pb-16 sm:pb-24 mx-auto px-12 grid grid-cols-1 md:grid-cols-2 justify-between items-center gap-2">
        {/* Left — Text */}
        <div>
          {/* Badge */}
          <div className="bg-green-50 text-[#5A9E40] px-3 py-1 rounded-full text-sm font-medium w-fit mb-6 flex items-center gap-2">
            <MessageCircle size={14} />
            <span>Trạm Hỏi Đáp</span>
          </div>

          {/* Headline */}
          <h1 className="font-heading text-5xl md:text-6xl font-extrabold text-[#2F4F4F] leading-tight mb-2">
            Tất tần tật những điều bạn cần biết về{" "}
            <span className="text-[#5A9E40]">Đậu</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg text-gray-500 leading-relaxed">
            Giải đáp các thắc mắc phổ biến về công cụ AI tinh chỉnh CV và
            luyện phỏng vấn 1-1.
          </p>
        </div>

        {/* Right — Mascot placeholder */}
        <div className="w-full  sm gap-4 flex flex-col items-center justify-center">
          <div className="w-[80%] min-h-[300px] md:min-h-[400px] relative text-[#5A9E40]">
            {/* Bean mascot SVG placeholder */}
            <Image
              src={"/qna.webp"}
              alt={"qna"}
              fill
              className="object-contain"
            />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════
          2. FLOATING FEATURE BAR
      ══════════════════════════════════════ */}
      <div className="-mt-16 relative z-10 px-6">
        <div className="max-w-6xl mx-auto bg-white rounded-3xl px-2 py-6 shadow-md border border-gray-100 flex flex-col md:flex-row justify-between items-center divide-y md:divide-y-0 md:divide-x divide-gray-100">
          {featureBarItems.map(({ icon: Icon, title, subtitle }) => (
            <div
              key={title}
              className="flex items-center gap-4 px-6 w-full py-4 md:py-0 first:pt-0 last:pb-0 md:first:pt-0 md:last:pb-0"
            >
              <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center shrink-0">
                <Icon size={20} className="text-[#5A9E40]" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[#2F4F4F]">{title}</p>
                <p className="text-xs text-gray-400">{subtitle}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ══════════════════════════════════════
          3. MAIN FAQ ACCORDION CARD
      ══════════════════════════════════════ */}
      <div className="px-6">
        <div className="max-w-6xl mx-auto bg-white rounded-[2rem] px-8 py-2 shadow-sm border border-gray-100 mt-4 mb-12">
          <Accordion type="single" collapsible className="w-full">
            {faqItems.map(({ icon: Icon, question, answer, summary }, index) => (
              <AccordionItem
                key={index}
                value={`item-${index}`}
                className="border-b border-gray-100 last:border-0 py-2 [&>h3]:mb-0"
              >
                <AccordionTrigger className="flex items-center gap-4 hover:no-underline text-base md:text-lg font-semibold text-[#2F4F4F] py-4 text-left [&>svg]:shrink-0 [&>svg]:text-gray-400">
                  {/* Icon pill */}
                  <span className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center text-[#5A9E40] shrink-0">
                    <Icon size={18} />
                  </span>
                  <span className="flex-1">{question}</span>
                </AccordionTrigger>

                <AccordionContent className="text-gray-600 leading-relaxed pl-14 pb-6 text-sm md:text-base">
                  <p>{answer}</p>

                  {/* "Tóm lại" summary box */}
                  <div className="mt-4 bg-green-50/50 border border-[#5A9E40]/20 rounded-xl p-4 flex gap-3 text-sm text-[#2F4F4F]">
                    <Leaf size={16} className="text-[#5A9E40] shrink-0 mt-0.5" />
                    <p>
                      <span className="font-semibold">Tóm lại: </span>
                      {summary}
                    </p>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
      <Footer />
    </main>
  );
}
