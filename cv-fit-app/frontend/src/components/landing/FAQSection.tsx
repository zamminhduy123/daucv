'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, FileText, Search, Shield, Languages, Mic } from 'lucide-react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

/* ─── 5 homepage questions — short answers (40–80 words) + deep-link to /qna ─── */
export const faqData = [
  {
    icon: Search,
    question: "CV chuẩn ATS là gì và làm sao để kiểm tra?",
    answer: "CV chuẩn ATS là CV có định dạng dễ đọc với hệ thống tuyển dụng tự động và có nội dung khớp với Job Description. Tránh bảng biểu phức tạp, icon đồ họa và chữ nhúng trong ảnh. Bạn có thể kiểm tra bằng cách so sánh từ khóa, kỹ năng và kinh nghiệm trong CV với JD.",
    deepLink: "/qna#cv-chuan-ats-la-gi",
    deepLinkText: "Xem giải thích đầy đủ về CV chuẩn ATS",
  },
  {
    icon: FileText,
    question: "Có nên dùng một CV để ứng tuyển nhiều công ty không?",
    answer: "Không nên. Mỗi JD thường yêu cầu những kỹ năng và từ khóa khác nhau. Nếu CV quá chung chung, hệ thống ATS sẽ không thấy đủ tín hiệu phù hợp. Cách tốt hơn là giữ một CV gốc rồi tinh chỉnh summary, kỹ năng và kinh nghiệm theo từng JD. Đậu làm việc này chỉ trong vài giây.",
    deepLink: "/qna#mot-cv-nhieu-cong-ty",
    deepLinkText: "Xem hướng dẫn tối ưu CV theo từng JD",
  },
  {
    icon: Shield,
    question: "Tại sao CV của tôi hay bị loại ở vòng gửi hồ sơ?",
    answer: "Hai nguyên nhân phổ biến nhất: thiếu từ khóa chuyên môn mà JD yêu cầu, và viết kinh nghiệm chung chung không có số liệu định lượng. Đậu phân tích CV, phát hiện lỗ hổng từ khóa và gợi ý cách viết lại theo chuẩn thực chiến.",
    deepLink: "/qna#loi-dinh-dang-cv",
    deepLinkText: "Xem các lỗi phổ biến khiến CV bị loại",
  },
  {
    icon: Languages,
    question: "Nên viết CV bằng tiếng Anh hay tiếng Việt?",
    answer: "Nguyên tắc vàng: JD viết bằng tiếng nào, CV nộp bằng tiếng đó. Nếu JD song ngữ, ưu tiên tiếng Anh để thể hiện năng lực. Đậu hỗ trợ phân tích và tối ưu CV bằng cả tiếng Anh lẫn tiếng Việt với độ chính xác cao.",
    deepLink: "/qna#ho-tro-tieng-anh",
    deepLinkText: "Xem Đậu hỗ trợ CV tiếng Anh thế nào",
  },
  {
    icon: Mic,
    question: "Làm sao để hết run khi phỏng vấn?",
    answer: "Cách duy nhất hiệu quả là luyện tập thực tế nhiều lần. Tính năng luyện phỏng vấn 1-1 của Đậu cho phép bạn thực hành trả lời bằng giọng nói theo câu hỏi bám sát JD thực tế, sau đó nhận đánh giá về nội dung, ngôn ngữ và độ tự tin ngay lập tức.",
    deepLink: "/qna#het-run-phong-van",
    deepLinkText: "Xem cách luyện phỏng vấn với AI",
  },
];

interface FAQSectionProps {
  showTitle?: boolean;
  showViewMore?: boolean;
}

export function FAQSection({ showTitle = true, showViewMore = true }: FAQSectionProps) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqData.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: { "@type": "Answer", text: faq.answer },
    })),
  };

  return (
    <section className="bg-(--bg)">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="max-w-3xl mx-auto py-20 px-6">
        {showTitle && (
          <motion.h2
            className="text-3xl font-bold text-center text-brand-text mb-12"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            Câu hỏi thường gặp
          </motion.h2>
        )}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ amount: 0.05, once: true }}
          variants={{
            hidden: {},
            visible: {
              transition: { staggerChildren: 0.08 },
            },
          }}
        >
          <Accordion type="single" collapsible className="space-y-4">
            {faqData.map(({ icon: Icon, question, answer, deepLink, deepLinkText }, index) => (
              <motion.div
                key={index}
                variants={{
                  hidden: { opacity: 0, y: 16 },
                  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] } },
                }}
              >
                <AccordionItem
                  value={`item-${index}`}
                  className="border border-gray-100 rounded-2xl px-6 bg-white shadow-sm transition-all duration-200 data-[state=open]:border-[#5A9E40]/40 data-[state=open]:bg-[#f6fcf4]"
                >
                  <AccordionTrigger className="flex items-center gap-4 hover:no-underline text-base md:text-lg font-semibold text-[#2F4F4F] py-5 text-left [&>svg]:text-gray-400 [&[data-state=open]>svg]:text-[#5A9E40]">
                    <Icon size={20} className="text-[#5A9E40] shrink-0" strokeWidth={2.5} />
                    <span className="flex-1">{question}</span>
                  </AccordionTrigger>
                  <AccordionContent className="text-gray-600 leading-relaxed pb-5 pl-9 md:pl-[3.25rem] text-sm md:text-base">
                    <p>{answer}</p>
                    {/* Deep-link to /qna anchor */}
                    <Link
                      href={deepLink}
                      className="inline-flex items-center gap-1.5 mt-3 text-xs font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors group"
                    >
                      {deepLinkText}
                      <ArrowRight size={12} className="transition-transform group-hover:translate-x-0.5" />
                    </Link>
                  </AccordionContent>
                </AccordionItem>
              </motion.div>
            ))}
          </Accordion>
        </motion.div>

        {/* View more link */}
        {showViewMore && (
          <motion.div
            className="mt-10 text-center"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.3 }}
          >
            <Link
              href="/qna"
              className="inline-flex items-center gap-2 text-sm font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors group"
            >
              Xem thêm cẩm nang & giải đáp thắc mắc 📚
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
          </motion.div>
        )}
      </div>
    </section>
  );
}
