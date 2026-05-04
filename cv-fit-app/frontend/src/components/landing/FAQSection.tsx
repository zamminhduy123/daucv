import React from 'react';
import Link from 'next/link';
import { ArrowRight, FileText, Search, Shield, Languages, Mic } from 'lucide-react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

export const faqData = [
  {
    icon: FileText,
    question: "Có nên dùng chung 1 CV để rải cho nhiều công ty không?",
    answer: "Không nên. Hơn 70% doanh nghiệp hiện nay dùng hệ thống ATS để quét từ khóa. Việc dùng chung 1 CV sẽ khiến bạn dễ bị loại. Hãy dùng Bé Đậu để tinh chỉnh CV khớp 100% với từng JD chỉ trong vài giây."
  },
  {
    icon: Search,
    question: "CV chuẩn ATS là gì và làm sao để kiểm tra?",
    answer: "CV chuẩn ATS là CV được thiết kế tối giản, không dùng bảng biểu phức tạp hay đồ họa che khuất chữ. Bạn có thể tải CV lên Daucv.com để AI chấm điểm 'Chuẩn ATS' miễn phí."
  },
  {
    icon: Shield,
    question: "Tại sao CV của tôi hay bị loại ở vòng gửi hồ sơ?",
    answer: "Thường do thiếu từ khóa chuyên môn hoặc viết kinh nghiệm không có số liệu định lượng. Đậu sẽ giúp bạn phát hiện từ khóa thiếu và gợi ý cách viết chuẩn thực chiến."
  },
  {
    icon: Languages,
    question: "Nên viết CV bằng tiếng Anh hay tiếng Việt?",
    answer: "Nguyên tắc vàng: JD viết bằng tiếng nào, CV nộp bằng tiếng đó. Daucv.com hỗ trợ tối ưu bằng cả tiếng Anh và tiếng Việt."
  },
  {
    icon: Mic,
    question: "Làm sao để hết run khi phỏng vấn?",
    answer: "Cách duy nhất là luyện tập thực tế. Tính năng 'Phỏng vấn 1-1' của Đậu cho phép bạn thực hành trả lời bằng giọng nói và nhận chấm điểm độ tự tin ngay lập tức."
  }
];

interface FAQSectionProps {
  /** Show the "Câu hỏi thường gặp" heading. Defaults to true. */
  showTitle?: boolean;
  /** Show the "Xem thêm" link to /qna. Defaults to true. */
  showViewMore?: boolean;
}

export function FAQSection({ showTitle = true, showViewMore = true }: FAQSectionProps) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": faqData.map((faq) => ({
      "@type": "Question",
      "name": faq.question,
      "acceptedAnswer": {
        "@type": "Answer",
        "text": faq.answer
      }
    }))
  };

  return (
    <section className="fade-up bg-(--bg)">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="max-w-3xl mx-auto py-20 px-6">
        {showTitle && (
          <h2 className="text-3xl font-bold text-center text-brand-text mb-12">
            Câu hỏi thường gặp
          </h2>
        )}
        <Accordion type="single" collapsible className="space-y-4">
          {faqData.map(({ icon: Icon, question, answer }, index) => (
            <AccordionItem
              key={index}
              value={`item-${index}`}
              className="border border-gray-100 rounded-2xl px-6 bg-white shadow-sm transition-all duration-200 data-[state=open]:border-[#5A9E40]/40 data-[state=open]:bg-[#f6fcf4]"
            >
              <AccordionTrigger className="flex items-center gap-4 hover:no-underline text-base md:text-lg font-semibold text-[#2F4F4F] py-5 text-left [&>svg]:text-gray-400 [&[data-state=open]>svg]:text-[#5A9E40]">
                <Icon size={20} className="text-[#5A9E40] shrink-0" strokeWidth={2.5} />
                <span className="flex-1">{question}</span>
              </AccordionTrigger>
              <AccordionContent className="text-gray-600 leading-relaxed pb-6 pl-9 md:pl-[3.25rem] text-sm md:text-base">
                {answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>

        {/* Link to full Q&A knowledge base */}
        {showViewMore && (
          <div className="mt-10 text-center">
            <Link
              href="/qna"
              className="inline-flex items-center gap-2 text-sm font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors group"
            >
              Xem thêm cẩm nang & giải đáp thắc mắc 📚
              <ArrowRight
                size={16}
                className="transition-transform group-hover:translate-x-1"
              />
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}
