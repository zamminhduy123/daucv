import type { Metadata } from "next";
import Image from "next/image";
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "@/components/landing/Footer";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Leaf, MessageCircle, Sparkles, Shield, Zap, TrendingUp } from "lucide-react";

const featureBarItems = [
  { icon: Sparkles, title: "AI Phân tích", subtitle: "Chính xác & Nhanh chóng" },
  { icon: Shield,   title: "Bảo mật 100%", subtitle: "Không lưu trữ dữ liệu" },
  { icon: Zap,      title: "Gợi ý thực chiến", subtitle: "Rõ ràng, dễ áp dụng" },
  { icon: TrendingUp, title: "Tăng tỷ lệ Đậu", subtitle: "Nhận nhiều lời mời hơn" },
];

/* ─────────────────────────────────────────────
   SEO Metadata — keyword-rich per recommendation
───────────────────────────────────────────── */
export const metadata: Metadata = {
  title: "Câu hỏi thường gặp về CV chuẩn ATS, AI sửa CV và luyện phỏng vấn | Đậu",
  description:
    "Giải đáp các câu hỏi thường gặp về CV chuẩn ATS, kiểm tra điểm ATS, tối ưu CV theo Job Description, AI sửa CV và luyện phỏng vấn bằng AI với Đậu.",
  alternates: {
    canonical: "https://daucv.com/qna",
  },
  openGraph: {
    title: "Câu hỏi thường gặp về CV chuẩn ATS, AI sửa CV và luyện phỏng vấn | Đậu",
    description:
      "Giải đáp các câu hỏi thường gặp về CV chuẩn ATS, tối ưu CV theo JD, AI sửa CV và luyện phỏng vấn AI.",
    url: "https://daucv.com/qna",
    type: "website",
    locale: "vi_VN",
  },
};

/* ─────────────────────────────────────────────
   FAQ Data — 20 questions in 5 topic groups
───────────────────────────────────────────── */
const faqGroups = [
  {
    id: "cv-chuan-ats",
    heading: "Câu hỏi về CV chuẩn ATS",
    items: [
      {
        id: "cv-chuan-ats-la-gi",
        question: "CV chuẩn ATS là gì?",
        answer:
          "CV chuẩn ATS là CV được viết và định dạng để hệ thống Applicant Tracking System có thể đọc đúng các thông tin như kinh nghiệm, kỹ năng, học vấn, vị trí ứng tuyển và từ khóa liên quan đến Job Description. Một CV chuẩn ATS thường tránh bố cục quá phức tạp, bảng nhiều cột, icon khó đọc, hình ảnh chứa chữ và các tiêu đề lạ như 'Hành trình của tôi'. Tuy nhiên, chuẩn ATS không chỉ là vấn đề định dạng — nội dung CV cũng cần có từ khóa và kỹ năng phù hợp với JD. Đậu giúp bạn so sánh CV với JD, phát hiện kỹ năng còn thiếu và gợi ý cách viết lại nội dung rõ ràng hơn.",
        summary: "CV chuẩn ATS = định dạng tối giản + nội dung khớp từ khóa JD.",
      },
      {
        id: "kiem-tra-cv-ats",
        question: "Làm sao biết CV của tôi có qua được ATS không?",
        answer:
          "Bạn có thể tự kiểm tra bằng cách: (1) copy toàn bộ nội dung CV vào Notepad — nếu thông tin hiển thị đúng thứ tự, có nghĩa ATS sẽ đọc được; (2) so sánh từ khóa trong CV với từ khóa trong JD để đảm bảo không bị lọc sớm. Cách nhanh nhất là tải CV và JD lên Đậu — AI sẽ chấm điểm 'Chuẩn ATS', tỷ lệ khớp từ khóa và gợi ý chỉnh sửa cụ thể chỉ trong vài giây.",
        summary: "Dùng Đậu để chấm điểm ATS và kiểm tra độ khớp từ khóa ngay lập tức.",
      },
      {
        id: "loi-dinh-dang-cv",
        question: "Những lỗi định dạng nào khiến CV bị ATS đọc sai?",
        answer:
          "Các lỗi phổ biến nhất gồm: sử dụng bảng nhiều cột để chia thông tin, dùng text box hoặc header/footer của Word, nhúng chữ vào hình ảnh, dùng font lạ không chuẩn, đặt tên các mục tiêu đề không rõ ràng (ví dụ: 'Về tôi' thay vì 'Kinh nghiệm làm việc'). Những lỗi này khiến ATS ghép thông tin sai chỗ hoặc bỏ sót hoàn toàn. Đậu phân tích cấu trúc CV và cảnh báo các vấn đề định dạng cụ thể.",
        summary: "Tránh bảng phức tạp, text box, chữ trong ảnh và heading lạ.",
      },
      {
        id: "cv-co-nen-de-anh",
        question: "CV có nên dùng bảng, icon hoặc ảnh đại diện không?",
        answer:
          "Bảng biểu và icon đồ họa phức tạp có thể làm ATS đọc sai thứ tự thông tin. Ảnh đại diện không bắt buộc và trong nhiều trường hợp (nhất là khối IT và công ty nước ngoài) còn được khuyên bỏ để tránh bias tuyển dụng. Nếu bạn muốn dùng ảnh, hãy đặt dưới dạng ảnh thật, không nhúng chữ vào ảnh. Nguyên tắc chung: đẹp là tốt, nhưng không được đánh đổi tính dễ đọc của máy.",
        summary: "Ưu tiên cấu trúc text rõ ràng, hạn chế icon và bảng phức tạp.",
      },
      {
        id: "pdf-hay-word",
        question: "File CV nên để PDF hay Word?",
        answer:
          "Luôn ưu tiên PDF trừ khi nhà tuyển dụng yêu cầu Word cụ thể. PDF giữ nguyên định dạng, font chữ trên mọi thiết bị và phần lớn ATS hiện đại đọc được PDF tốt. File Word dễ bị lỗi font khi mở trên máy khác. Đậu xử lý và phân tích file PDF CV của bạn mượt mà, không cần chuyển đổi.",
        summary: "PDF là lựa chọn an toàn nhất trong hầu hết mọi trường hợp.",
      },
    ],
  },
  {
    id: "toi-uu-cv-theo-jd",
    heading: "Câu hỏi về tối ưu CV theo Job Description",
    items: [
      {
        id: "mot-cv-nhieu-cong-ty",
        question: "Có nên dùng một CV để ứng tuyển nhiều công ty không?",
        answer:
          "Không nên dùng cùng một CV cho tất cả công ty, đặc biệt khi các vị trí có Job Description khác nhau. Mỗi JD thường nhấn mạnh những kỹ năng, công cụ, kinh nghiệm và trách nhiệm riêng. Nếu CV của bạn quá chung chung, hệ thống ATS hoặc nhà tuyển dụng có thể không thấy đủ tín hiệu phù hợp. Cách tốt hơn là giữ một CV gốc, sau đó tùy chỉnh phần summary, kỹ năng và kinh nghiệm theo từng JD. Đậu giúp bạn phân tích độ khớp giữa CV và JD để biết nên bổ sung từ khóa, kỹ năng hoặc thành tựu nào trước khi gửi hồ sơ.",
        summary: "Một CV gốc, tinh chỉnh theo từng JD. Đậu làm việc này chỉ trong vài giây.",
      },
      {
        id: "toi-uu-cv-theo-jd-la-gi",
        question: "Tối ưu CV theo Job Description là gì?",
        answer:
          "Tối ưu CV theo JD là quá trình điều chỉnh ngôn ngữ, từ khóa, thứ tự kỹ năng và cách mô tả kinh nghiệm trong CV để phản ánh đúng những gì JD yêu cầu. Điều này giúp CV vượt qua ATS và gây ấn tượng với HR khi họ đọc. Đậu tự động phân tích JD, trích xuất từ khóa quan trọng và so sánh với CV hiện tại của bạn, sau đó đề xuất những thay đổi cụ thể.",
        summary: "Tối ưu CV theo JD giúp vượt ATS và tạo ấn tượng đúng chỗ với HR.",
      },
      {
        id: "thieu-ky-nang-nao",
        question: "Làm sao biết CV của tôi thiếu kỹ năng nào so với JD?",
        answer:
          "Cách thủ công là đọc JD kỹ, highlight các từ khóa kỹ năng, công cụ, kinh nghiệm rồi đối chiếu với CV. Tuy nhiên, cách này tốn thời gian và dễ bỏ sót. Đậu tự động hóa bước này — chỉ cần paste JD và CV vào, AI sẽ liệt kê ngay các từ khóa còn thiếu, xếp loại theo mức độ ưu tiên (quan trọng / nên có) và gợi ý cách bổ sung.",
        summary: "Đậu phân tích và liệt kê từ khóa còn thiếu trong vài giây thay cho bạn.",
      },
      {
        id: "copy-tu-khoa-jd",
        question: "Có nên copy nguyên từ khóa trong JD vào CV không?",
        answer:
          "Không nên copy nguyên văn một cách cứng nhắc. Hãy lồng ghép từ khóa một cách tự nhiên vào các câu mô tả kinh nghiệm, thành tựu cụ thể. Ví dụ thay vì thêm 'Python' vào phần kỹ năng một cách đơn lẻ, hãy viết 'Xây dựng pipeline xử lý dữ liệu bằng Python, rút ngắn thời gian báo cáo 40%'. Đậu gợi ý cách viết lại cụ thể từng câu, đảm bảo từ khóa xuất hiện tự nhiên và thuyết phục.",
        summary: "Lồng ghép từ khóa vào câu có số liệu cụ thể, không liệt kê rời rạc.",
      },
      {
        id: "viet-lai-kinh-nghiem",
        question: "Làm sao viết lại kinh nghiệm làm việc cho phù hợp với JD?",
        answer:
          "Công thức hiệu quả nhất là: Động từ hành động + Nhiệm vụ cụ thể + Kết quả định lượng. Ví dụ: 'Phát triển tính năng thanh toán online bằng React và Node.js, giúp tỷ lệ chuyển đổi tăng 25%'. Khi tối ưu theo JD, hãy đảm bảo các từ khóa công nghệ và kỹ năng trong JD xuất hiện trong phần mô tả kinh nghiệm. Đậu đề xuất cụ thể từng bullet point cần viết lại và đưa ra phiên bản đã tối ưu.",
        summary: "Động từ mạnh + nhiệm vụ cụ thể + số liệu = bullet point ghi điểm.",
      },
    ],
  },
  {
    id: "ai-sua-cv",
    heading: "Câu hỏi về AI sửa CV",
    items: [
      {
        id: "ai-tot-hon-tu-sua",
        question: "AI sửa CV có tốt hơn tự sửa thủ công không?",
        answer:
          "AI không thay thế hoàn toàn được sự hiểu biết của bạn về kinh nghiệm của mình, nhưng AI giỏi hơn người ở một số điểm quan trọng: phân tích từ khóa JD toàn diện hơn, gợi ý ngôn ngữ chuyên nghiệp hơn và xử lý nhanh hơn nhiều. Kết hợp tốt nhất là dùng AI để phân tích và gợi ý, sau đó bạn xem xét và quyết định chấp nhận hay điều chỉnh. Đậu được thiết kế theo hướng này — AI đề xuất, bạn quyết định.",
        summary: "Dùng AI để phân tích và gợi ý, bạn giữ quyền quyết định cuối cùng.",
      },
      {
        id: "dau-khac-chatgpt",
        question: "Đậu khác gì so với việc dùng ChatGPT để sửa CV?",
        answer:
          "ChatGPT là công cụ đa năng, không được huấn luyện riêng cho việc đối chiếu CV với JD. Khi bạn dùng ChatGPT, bạn phải tự paste cả CV lẫn JD, tự đặt câu hỏi đúng và tự đánh giá kết quả. Đậu được xây dựng chuyên biệt cho bài toán này: có workflow rõ ràng, chấm điểm ATS tự động, liệt kê từ khóa còn thiếu, gợi ý viết lại từng bullet point cụ thể và hỗ trợ luyện phỏng vấn dựa trên CV + JD của bạn.",
        summary: "Đậu chuyên biệt cho CV-JD matching, không cần bạn tự prompt phức tạp.",
      },
      {
        id: "ai-bia-kinh-nghiem",
        question: "AI có viết sai hoặc phóng đại kinh nghiệm của tôi không?",
        answer:
          "Đậu không tự sáng tác kinh nghiệm. AI hoạt động dựa trên nội dung kinh nghiệm bạn đã cung cấp trong CV, sau đó đề xuất cách diễn đạt chuyên nghiệp hơn, thêm động từ mạnh và lồng ghép từ khóa từ JD một cách tự nhiên. Bạn luôn là người quyết định có áp dụng gợi ý hay không. Mọi thay đổi đều hiển thị rõ ràng để bạn so sánh bản gốc và bản đề xuất.",
        summary: "AI tối ưu cách bạn trình bày, không tạo thông tin giả.",
      },
      {
        id: "chua-co-kinh-nghiem",
        question: "Tôi chưa có nhiều kinh nghiệm thì AI có giúp được không?",
        answer:
          "Có. Với Fresher hoặc người đang chuyển ngành, Đậu giúp bạn 'dịch' những trải nghiệm học tập, đồ án, hoạt động ngoại khóa và kỹ năng mềm thành ngôn ngữ chuyên nghiệp mà nhà tuyển dụng quan tâm. AI còn giúp bạn xác định từ khóa kỹ năng nào trong JD bạn đã có nhưng chưa thể hiện rõ trong CV.",
        summary: "Đậu giúp Fresher trình bày tiềm năng thuyết phục hơn dù kinh nghiệm còn ít.",
      },
      {
        id: "ho-tro-tieng-anh",
        question: "Đậu có hỗ trợ CV tiếng Anh không?",
        answer:
          "Có. Đậu hỗ trợ đầy đủ cả CV tiếng Việt và tiếng Anh. AI tự động nhận diện ngôn ngữ chính của CV và JD, sau đó phân tích và đề xuất viết lại bằng đúng ngôn ngữ đó. Điều này đặc biệt hữu ích nếu bạn đang ứng tuyển vào các công ty nước ngoài hoặc vị trí yêu cầu CV tiếng Anh.",
        summary: "Đậu phân tích và tối ưu CV cả tiếng Việt lẫn tiếng Anh.",
      },
    ],
  },
  {
    id: "luyen-phong-van-ai",
    heading: "Câu hỏi về luyện phỏng vấn AI",
    items: [
      {
        id: "luyen-phong-van-hoat-dong-the-nao",
        question: "Luyện phỏng vấn với AI hoạt động như thế nào?",
        answer:
          "Đậu tạo ra một buổi phỏng vấn thử 1-1 dựa trên CV và JD cụ thể của bạn. AI đóng vai người phỏng vấn, đặt câu hỏi phù hợp với từng vị trí (HR, chuyên môn kỹ thuật hoặc quản lý). Bạn trả lời bằng giọng nói hoặc văn bản, sau đó nhận phản hồi chi tiết về nội dung câu trả lời, ngôn ngữ và điểm cần cải thiện ngay lập tức.",
        summary: "Phỏng vấn thử 1-1 với AI theo đúng CV và JD của bạn, có phản hồi tức thì.",
      },
      {
        id: "cau-hoi-dua-tren-cv-jd",
        question: "Câu hỏi phỏng vấn có dựa trên CV và JD của tôi không?",
        answer:
          "Có. Đây là điểm khác biệt lớn nhất của Đậu so với các ứng dụng luyện phỏng vấn thông thường. AI đọc JD của vị trí bạn đang ứng tuyển và CV của bạn, sau đó sinh ra câu hỏi phù hợp — không phải câu hỏi chung chung. Ví dụ nếu JD yêu cầu kinh nghiệm React và CV bạn có dự án dùng Vue, AI sẽ hỏi về sự khác biệt và khả năng chuyển đổi của bạn.",
        summary: "Câu hỏi được tạo riêng theo CV + JD của bạn, không phải câu hỏi mẫu chung.",
      },
      {
        id: "het-run-phong-van",
        question: "Làm sao để bớt run khi phỏng vấn?",
        answer:
          "Tâm lý run khi phỏng vấn đến từ sự thiếu chuẩn bị và chưa quen với áp lực. Cách duy nhất hiệu quả là luyện tập thực tế nhiều lần. Tính năng luyện phỏng vấn của Đậu cho phép bạn thực hành trả lời bằng giọng nói trong môi trường mô phỏng sát thực tế, nhận điểm đánh giá độ tự tin và gợi ý cải thiện sau mỗi câu. Luyện đủ nhiều, bạn sẽ không còn thấy xa lạ với áp lực phỏng vấn.",
        summary: "Luyện thật nhiều với AI để quen áp lực trước khi vào phỏng vấn thật.",
      },
      {
        id: "luyen-phong-van-fresher",
        question: "Tôi có thể luyện phỏng vấn cho vị trí Fresher không?",
        answer:
          "Hoàn toàn có thể. Đậu hỗ trợ luyện phỏng vấn cho mọi cấp độ từ Fresher đến Senior. Với Fresher, AI sẽ tập trung vào các câu hỏi phù hợp như giới thiệu bản thân, dự án học tập, mục tiêu nghề nghiệp và các câu hỏi hành vi (behavioral questions). Bạn cũng có thể chọn loại vòng phỏng vấn: HR, chuyên môn, quản lý hoặc tổng hợp.",
        summary: "Đậu hỗ trợ Fresher với câu hỏi phù hợp theo cấp độ và loại vòng phỏng vấn.",
      },
    ],
  },
  {
    id: "bao-mat",
    heading: "Câu hỏi về bảo mật dữ liệu",
    items: [
      {
        id: "du-lieu-cv-co-duoc-luu",
        question: "Đậu có lưu trữ CV hoặc dữ liệu cá nhân của tôi không?",
        answer:
          "Không. Đậu không lưu trữ CV, nội dung JD hay bất kỳ thông tin cá nhân nào của bạn sau khi phiên làm việc kết thúc. Dữ liệu chỉ được xử lý trong phiên để tạo ra phân tích và gợi ý, sau đó không được giữ lại trên server. Bạn có thể hoàn toàn yên tâm khi chia sẻ CV để phân tích.",
        summary: "CV và dữ liệu của bạn không được lưu trữ. Bảo mật 100%.",
      },
    ],
  },
];

/* ─────────────────────────────────────────────
   JSON-LD — mirrors every visible answer
───────────────────────────────────────────── */
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqGroups.flatMap((g) =>
    g.items.map((f) => ({
      "@type": "Question",
      name: f.question,
      acceptedAnswer: { "@type": "Answer", text: f.answer },
    }))
  ),
};

/* ═══════════════════════════════════════════
   PAGE
═══════════════════════════════════════════ */
export default function QnAPage() {
  return (
    <main className="min-h-screen bg-[#FEFDF8] text-[#2F4F4F]">
      {/* Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <LandingNavbar />

      {/* ── Hero — 2-column with mascot ── */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 grid grid-cols-1 md:grid-cols-2 items-center gap-8 pb-16">
        {/* Left — text */}
        <div>
          <div className="bg-green-50 text-[#5A9E40] px-3 py-1 rounded-full text-sm font-medium w-fit mb-6 flex items-center gap-2">
            <MessageCircle size={14} />
            <span>Trạm Hỏi Đáp</span>
          </div>

          {/* H1 — visual headline (keyword-rich title is in <head>) */}
          <h1 className="font-heading text-5xl md:text-6xl font-extrabold text-[#2F4F4F] leading-tight mb-4">
            Giải đáp về CV &amp; <span className="text-[#5A9E40]">Ứng dụng Đậu</span>
          </h1>

          {/* Keyword-rich subtitle — picked up by Google */}
          <p className="text-lg text-gray-500 leading-relaxed">
            Mọi thắc mắc về <strong className="font-medium text-[#2F4F4F]">CV chuẩn ATS</strong>, tối ưu CV theo Job Description, AI sửa CV và luyện phỏng vấn AI đều được giải đáp tại đây.
          </p>
        </div>

        {/* Right — mascot */}
        <div className="w-full flex flex-col items-center justify-center">
          <div className="w-[80%] min-h-[300px] md:min-h-[400px] relative">
            <Image src="/qna.webp" alt="Bé Đậu giải đáp câu hỏi CV chuẩn ATS" fill className="object-contain" />
          </div>
        </div>
      </section>

      {/* ── Floating feature bar ── */}
      <div className="-mt-10 md:-mt-16 relative z-10 px-6 mb-6">
        <div className="max-w-6xl mx-auto bg-white rounded-3xl px-2 py-6 shadow-md border border-gray-100 flex flex-col md:flex-row justify-between items-center divide-y md:divide-y-0 md:divide-x divide-gray-100">
          {featureBarItems.map(({ icon: Icon, title, subtitle }) => (
            <div key={title} className="flex items-center gap-4 px-6 w-full py-4 md:py-0">
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

      {/* ── Grouped FAQ Sections ── */}
      <div className="max-w-6xl mt-12 mx-auto px-6 pb-20 space-y-14">
        {faqGroups.map((group) => (
          <section key={group.id} id={group.id} aria-labelledby={`heading-${group.id}`}>
            {/* H2 topic heading */}
            <h2
              id={`heading-${group.id}`}
              className="text-lg font-bold text-[#2F4F4F] mb-4 pb-2 border-b border-gray-100 flex items-center gap-2"
            >
              <span className="w-1.5 h-5 bg-[var(--primary)] rounded-full inline-block" />
              {group.heading}
            </h2>

            <Accordion type="single" collapsible className="space-y-3">
              {group.items.map((faq) => (
                <AccordionItem
                  key={faq.id}
                  id={faq.id}
                  value={faq.id}
                  className="border border-gray-100 rounded-2xl px-5 bg-white shadow-sm transition-all duration-200 data-[state=open]:border-[#5A9E40]/40 data-[state=open]:bg-[#f6fcf4]"
                >
                  <AccordionTrigger className="hover:no-underline text-sm md:text-base font-semibold text-[#2F4F4F] py-4 text-left">
                    {faq.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-gray-600 leading-relaxed pb-5 text-sm md:text-base">
                    <p>{faq.answer}</p>
                    {faq.summary && (
                      <div className="mt-4 bg-green-50/60 border border-[#5A9E40]/20 rounded-xl p-3 flex gap-2 text-sm text-[#2F4F4F]">
                        <Leaf size={15} className="text-[#5A9E40] shrink-0 mt-0.5" />
                        <p><span className="font-semibold">Tóm lại: </span>{faq.summary}</p>
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </section>
        ))}
      </div>

      <Footer />
    </main>
  );
}
