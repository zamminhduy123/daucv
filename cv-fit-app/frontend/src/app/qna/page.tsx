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
  Target,
  FileDown,
  LayoutTemplate,
  User,
  PenTool,
  GraduationCap,
  ListChecks,
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
    icon: Target,
    question: "CV tailored (tinh chỉnh theo JD) là gì và vì sao cần thiết?",
    answer:
      "CV tailored là CV được điều chỉnh nội dung (từ khóa, kỹ năng, kinh nghiệm) sao cho khớp nhất với mô tả công việc (JD) của vị trí bạn đang ứng tuyển. Việc gửi 1 CV chung cho mọi công ty dễ khiến bạn bị loại vì thiếu từ khóa. Đậu giúp bạn tự động so sánh CV với JD và gợi ý tinh chỉnh chỉ trong vài giây, giúp tăng gấp 3 lần tỷ lệ được gọi phỏng vấn.",
    summary:
      "CV tailored là CV 'đo ni đóng giày' cho từng JD. Dùng Đậu để tối ưu nhanh chóng.",
  },
  {
    icon: Search,
    question: "CV chuẩn ATS là gì và làm sao để kiểm tra?",
    answer:
      "CV chuẩn ATS là CV được thiết kế tối giản, dễ đọc bởi phần mềm lọc hồ sơ tự động (Applicant Tracking System). Nó không chứa bảng biểu phức tạp, đồ họa che khuất chữ. Hơn 70% doanh nghiệp đang dùng ATS. Bạn có thể tải CV lên Đậu để AI chấm điểm 'Chuẩn ATS' miễn phí và biết ngay CV của mình có dễ đọc với máy không.",
    summary:
      "CV chuẩn ATS = thiết kế tối giản, text-based. Đậu giúp bạn chấm điểm ATS miễn phí.",
  },
  {
    icon: Shield,
    question: "Tại sao CV của tôi hay bị loại ở vòng gửi hồ sơ?",
    answer:
      "Thường do hai nguyên nhân chính: (1) thiếu từ khóa chuyên môn mà JD yêu cầu, (2) viết kinh nghiệm chung chung, không có số liệu định lượng (ví dụ: 'tăng trưởng doanh thu' thay vì 'tăng 20% doanh thu'). Đậu sẽ phân tích CV, phát hiện lỗ hổng từ khóa và gợi ý cách viết lại theo chuẩn thực chiến.",
    summary:
      "Thiếu từ khóa và thiếu số liệu định lượng là lý do chính. Đậu giúp bạn vá đúng những lỗ hổng này.",
  },
  {
    icon: Languages,
    question: "Nên viết CV bằng tiếng Anh hay tiếng Việt?",
    answer:
      "Nguyên tắc vàng: JD viết bằng tiếng nào, CV nộp bằng tiếng đó. Nếu JD song ngữ, ưu tiên tiếng Anh để thể hiện năng lực. Đậu (daucv.com) hỗ trợ phân tích, chấm điểm và tối ưu CV bằng cả tiếng Anh và tiếng Việt với độ chính xác cao.",
    summary:
      "JD tiếng nào, CV tiếng đó. Đậu hỗ trợ cả Anh lẫn Việt hoàn hảo.",
  },
  {
    icon: FileDown,
    question: "File CV nên dùng PDF hay Word để qua ATS?",
    answer:
      "Bạn luôn nên lưu và gửi CV dưới dạng PDF (trừ khi nhà tuyển dụng đặc biệt yêu cầu file Word). PDF giúp giữ nguyên định dạng, font chữ trên mọi thiết bị và hệ thống của nhà tuyển dụng. Hệ thống phân tích của Đậu xử lý file PDF rất mượt mà.",
    summary:
      "Luôn ưu tiên xuất và gửi CV bằng file PDF để không bị lỗi hiển thị.",
  },
  {
    icon: LayoutTemplate,
    question: "CV thiết kế quá đẹp, nhiều hình ảnh có dễ qua vòng ATS không?",
    answer:
      "Không hẳn. CV quá nhiều cột, bảng biểu phức tạp, dùng ảnh hoặc infographic thay cho chữ có thể khiến hệ thống ATS đọc sai hoặc bỏ sót thông tin quan trọng. Đẹp là tốt, nhưng phải 'dễ đọc' với máy. Bạn nên ưu tiên cấu trúc rõ ràng, chuyên nghiệp.",
    summary:
      "Đừng hy sinh tính dễ đọc để lấy thiết kế phức tạp. Hãy dùng bố cục rõ ràng.",
  },
  {
    icon: ListChecks,
    question: "Có cần điều chỉnh cả phần kỹ năng (skills) theo từng JD không?",
    answer:
      "Chắc chắn rồi! Mỗi vị trí sẽ ưu tiên những công cụ và kỹ năng khác nhau. Ví dụ: Data Analyst có thể yêu cầu SQL, Python; nhưng công ty khác lại yêu cầu PowerBI. Đậu sẽ quét JD và đối chiếu với CV của bạn để chỉ ra ngay những kỹ năng bạn đang thiếu cần bổ sung.",
    summary:
      "Phần kỹ năng cũng cần match 100% với yêu cầu của JD. Đậu sẽ chỉ ra kỹ năng bạn đang thiếu.",
  },
  {
    icon: User,
    question: "Tại Việt Nam, CV có bắt buộc phải có ảnh chân dung không?",
    answer:
      "Tùy thuộc vào ngành nghề. Tại Việt Nam, ảnh CV vẫn được ưa chuộng trong các ngành dịch vụ, tư vấn, sale, marketing. Tuy nhiên, với khối IT, kỹ thuật, data hoặc các công ty đa quốc gia, ảnh là không bắt buộc. Nếu dùng, hãy chọn ảnh rõ mặt, trang phục lịch sự.",
    summary:
      "Tùy ngành nghề và văn hóa công ty. Khối kỹ thuật/IT hoặc công ty quốc tế thường không cần ảnh.",
  },
  {
    icon: PenTool,
    question: "Công cụ AI của Đậu có 'bịa' kinh nghiệm viết CV thay tôi không?",
    answer:
      "Tuyệt đối không. Đậu không tự sáng tác kinh nghiệm giả. AI của chúng tôi hoạt động bằng cách đọc kinh nghiệm bạn đã có, sau đó đề xuất cách diễn đạt chuyên nghiệp hơn, thêm động từ mạnh, và lồng ghép từ khóa từ JD sao cho thật tự nhiên và thuyết phục nhất.",
    summary:
      "Đậu tối ưu cách bạn kể câu chuyện năng lực của mình, chứ không tạo ra thông tin giả.",
  },
  {
    icon: GraduationCap,
    question: "Sinh viên mới ra trường (Fresher) chưa có kinh nghiệm thì viết CV thế nào?",
    answer:
      "Hãy tập trung vào học vấn, đồ án tốt nghiệp, các dự án bài tập lớn, hoạt động ngoại khóa, kỹ năng mềm và chứng chỉ liên quan. Đậu sẽ giúp bạn 'dịch' những trải nghiệm học tập này thành những kỹ năng thực tế mà nhà tuyển dụng đang tìm kiếm.",
    summary:
      "Nhấn mạnh vào dự án môn học, hoạt động ngoại khóa và tiềm năng học hỏi.",
  },
  {
    icon: Mic,
    question: "Làm sao để hết run khi đi phỏng vấn thực tế?",
    answer:
      "Cách duy nhất là luyện tập thực tế, lặp đi lặp lại. Tính năng 'Phỏng vấn 1-1' của Đậu cho phép bạn thực hành trả lời bằng giọng nói theo các câu hỏi bám sát JD thực tế, sau đó nhận phân tích chi tiết về nội dung, ngôn ngữ và độ tự tin ngay lập tức.",
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
            Giải đáp về CV & <span className="text-[#5A9E40]">Ứng dụng Đậu</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg text-gray-500 leading-relaxed">
            Mọi thắc mắc của bạn về kiến thức CV chuẩn ATS và cách dùng AI của Đậu để chốt deal sự nghiệp đều được giải đáp tại đây.
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
