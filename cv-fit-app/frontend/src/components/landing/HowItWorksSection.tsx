import type { HowItWorksStep } from "@/types";

const STEPS: HowItWorksStep[] = [
  {
    n: "01",
    t: "Gieo mầm CV",
    d: "Tải file PDF của bạn lên. Đậu sẽ phân tích hồ sơ của bạn một cách thấu đáo.",
  },
  {
    n: "02",
    t: "Chăm chút JD",
    d: "Dán mô tả công việc. Đậu sẽ tìm ra điểm chạm hoàn hảo giữa bạn và nhà tuyển dụng.",
  },
  {
    n: "03",
    t: "Gặt hái kết quả",
    d: "Nhận CV tối ưu, điểm tương thích và bắt đầu luyện phỏng vấn 1-1.",
  },
];

export default function HowItWorksSection() {
  return (
    <section id="cách-hoạt-động" className="max-w-7xl mx-auto" style={{ padding: "6rem 3rem" }}>
      <div
        className="text-[#F9F9F2] relative overflow-hidden"
        style={{ backgroundColor: "#2F4F4F", borderRadius: 32, padding: "5rem" }}
      >
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#98C18E] mb-6">
          Quy trình &quot;nảy mầm&quot;
        </p>
        <h2
          className="font-heading font-bold leading-tight max-w-[800px] mb-16"
          style={{ fontSize: "clamp(2.5rem,4.5vw,3.5rem)" }}
        >
          Ba bước đơn giản.<br />Cơ hội việc làm rộng mở.
        </h2>

        <div className="grid grid-cols-3 gap-16">
          {STEPS.map((s) => (
            <div
              key={s.n}
              className="pt-8"
              style={{ borderTop: "2px solid rgba(152,193,142,0.3)" }}
            >
              <div
                className="font-mono font-bold text-[#98C18E] mb-6"
                style={{ fontSize: "1.25rem" }}
              >
                {s.n}
              </div>
              <h3 className="font-heading font-bold mb-4" style={{ fontSize: "1.75rem" }}>
                {s.t}
              </h3>
              <p
                className="leading-relaxed"
                style={{ color: "rgba(249,249,242,0.8)", fontSize: "1.1rem" }}
              >
                {s.d}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
