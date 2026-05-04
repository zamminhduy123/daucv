import React from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

const faqData = [
  {
    question: "Có nên dùng chung 1 CV để rải cho nhiều công ty không?",
    answer: "Không nên. Hơn 70% doanh nghiệp hiện nay dùng hệ thống ATS để quét từ khóa. Việc dùng chung 1 CV sẽ khiến bạn dễ bị loại. Hãy dùng Bé Đậu để tinh chỉnh CV khớp 100% với từng JD chỉ trong vài giây."
  },
  {
    question: "CV chuẩn ATS là gì và làm sao để kiểm tra?",
    answer: "CV chuẩn ATS là CV được thiết kế tối giản, không dùng bảng biểu phức tạp hay đồ họa che khuất chữ. Bạn có thể tải CV lên Daucv.com để AI chấm điểm 'Chuẩn ATS' miễn phí."
  },
  {
    question: "Tại sao CV của tôi hay bị loại ở vòng gửi hồ sơ?",
    answer: "Thường do thiếu từ khóa chuyên môn hoặc viết kinh nghiệm không có số liệu định lượng. Đậu sẽ giúp bạn phát hiện từ khóa thiếu và gợi ý cách viết chuẩn thực chiến."
  },
  {
    question: "Nên viết CV bằng tiếng Anh hay tiếng Việt?",
    answer: "Nguyên tắc vàng: JD viết bằng tiếng nào, CV nộp bằng tiếng đó. Daucv.com hỗ trợ tối ưu bằng cả tiếng Anh và tiếng Việt."
  },
  {
    question: "Làm sao để hết run khi phỏng vấn?",
    answer: "Cách duy nhất là luyện tập thực tế. Tính năng 'Phỏng vấn 1-1' của Đậu cho phép bạn thực hành trả lời bằng giọng nói và nhận chấm điểm độ tự tin ngay lập tức."
  }
];

export function FAQSection() {
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
        <h2 className="text-3xl font-bold text-center text-brand-text mb-12">
          Câu hỏi thường gặp
        </h2>
        <Accordion type="single" collapsible className="space-y-4">
          {faqData.map((faq, index) => (
            <AccordionItem
              key={index}
              value={`item-${index}`}
              className="border border-gray-200 rounded-xl px-4 bg-white shadow-sm data-[state=open]:border-brand-border"
            >
              <AccordionTrigger className="text-brand-text hover:no-underline hover:text-brand-text/80 text-left font-medium py-4">
                {faq.question}
              </AccordionTrigger>
              <AccordionContent className="text-gray-600 leading-relaxed pb-4">
                {faq.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
