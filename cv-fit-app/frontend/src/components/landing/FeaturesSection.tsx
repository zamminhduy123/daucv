import { Sparkles, FileText, MessageSquare } from "lucide-react";
import type { FeatureItem } from "@/types";

const FEATURES: FeatureItem[] = [
  {
    icon: Sparkles,
    title: "Điểm tương thích",
    body: "AI quét JD và chấm điểm độ phù hợp. Thiếu kỹ năng nào, Đậu sẽ giúp bạn bổ sung ngay kỹ năng đó.",
  },
  {
    icon: FileText,
    title: "CV chuẩn, phỏng vấn chất",
    body: "CV được viết lại để làm nổi bật các điểm mạnh mà nhà tuyển dụng đang tìm kiếm — chuyên nghiệp và ấn tượng.",
  },
  {
    icon: MessageSquare,
    title: "Tập dượt với Bé Đậu",
    body: "Phỏng vấn thử bằng tiếng Anh hoặc tiếng Việt. Nhận xét chi tiết ngay sau mỗi câu trả lời để bạn rút kinh nghiệm.",
  },
];

export default function FeaturesSection() {
  return (
    <section id="Lợi ích" className="max-w-7xl mx-auto" style={{ padding: "6rem 3rem" }}>
      {/* Header */}
      <div
        className="grid gap-16 items-start"
        style={{ gridTemplateColumns: "1fr 1fr", marginBottom: "5rem" }}
      >
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#98C18E] mb-6">
            Lợi ích từ Bé Đậu
          </p>
          <h2
            className="font-heading font-bold leading-tight text-[#2F4F4F]"
            style={{ fontSize: "clamp(2.5rem,5vw,4rem)" }}
          >
            Biến JD khó thành thư mời nhận việc.
          </h2>
        </div>
        <p className="text-[#5A6D6D] leading-relaxed pt-10" style={{ fontSize: "1.25rem" }}>
          Đậu không chỉ chấm điểm, chúng tôi đồng hành cùng bạn từ lúc sửa từng dấu phẩy
          trên CV cho đến khi bạn tự tin trả lời phỏng vấn.
        </p>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-3 gap-8">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <div key={title} className="feature-card">
            <div
              className="flex items-center justify-center rounded-2xl mb-7"
              style={{
                width: 56, height: 56,
                backgroundColor: "rgba(152,193,142,0.15)",
              }}
            >
              <Icon size={24} color="#98C18E" />
            </div>
            <h3 className="font-heading font-bold text-[#2F4F4F] mb-4" style={{ fontSize: "1.5rem" }}>
              {title}
            </h3>
            <p className="text-[#5A6D6D] leading-relaxed">{body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
