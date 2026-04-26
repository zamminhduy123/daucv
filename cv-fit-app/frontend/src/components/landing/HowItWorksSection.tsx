import Image from "next/image";
import type { HowItWorksStep } from "@/types";

interface StepData extends HowItWorksStep {
  img: string;
}

const STEPS: StepData[] = [
  {
    n: "1",
    t: "Tải CV & JD",
    d: "Tải lên CV của bạn và mô tả công việc (JD).",
    img: "/upload.webp",
  },
  {
    n: "2",
    t: "AI phân tích",
    d: "Đậu sẽ phân tích, chấm điểm và gợi ý cách cải thiện.",
    img: "/analyze.webp",
  },
  {
    n: "3",
    t: "Luyện tập & tự tin",
    d: "Luyện phỏng vấn 1-1 và nhận góp ý chi tiết để tự tin chinh phục nhà tuyển dụng.",
    img: "/trophy.webp",
  },
];

export default function HowItWorksSection() {
  return (
    <section id="cách-hoạt-động" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-20">
      <div className="text-center mb-16">
        <h2 className="font-heading font-bold text-[#2F4F4F] text-3xl md:text-4xl mb-4">
          Bắt đầu với Đậu chỉ trong 3 bước
        </h2>
      </div>

      <div className="flex flex-col lg:flex-row items-stretch justify-between gap-8 relative">
        {STEPS.map((s, idx) => (
          <div key={s.n} className="flex flex-1 items-stretch w-full lg:w-auto">
            {/* Step Card */}
            <div className="bg-white rounded-3xl pt-8 pb-16 px-8 border border-gray-100 shadow-sm hover:shadow-md transition-shadow relative flex-1 min-h-[220px] overflow-hidden group">
              {/* Image as background element with offset */}
              <div className="absolute -bottom-4 -right-4 w-40 h-40 opacity-20 lg:opacity-100 lg:w-44 lg:h-44 transition-transform group-hover:scale-110 duration-500">
                <Image
                  src={s.img}
                  alt={s.t}
                  fill
                  className="object-contain"
                />
              </div>

              <div className="relative z-10">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-10 h-10 rounded-full bg-[var(--primary)] text-white flex items-center justify-center font-bold text-lg shadow-sm">
                    {s.n}
                  </div>
                  <h3 className="font-heading font-bold text-[#2F4F4F] text-xl">
                    {s.t}
                  </h3>
                </div>
                <p className="text-[#5A6D6D] text-sm leading-relaxed max-w-[240px] mr-18">
                  {s.d}
                </p>
              </div>
            </div>

            {/* Connector - only show between cards on desktop */}
            {/* {idx < STEPS.length - 1 && (
              <div className="hidden lg:block w-16 flex-shrink-0 px-2">
                <svg width="100%" height="20" viewBox="0 0 60 20" fill="none">
                  <path 
                    d="M2 10C15 2 45 18 58 10" 
                    stroke="var(--primary)" 
                    strokeWidth="2" 
                    strokeDasharray="4 4" 
                    opacity="0.3"
                  />
                </svg>
              </div>
            )} */}
          </div>
        ))}
      </div>
    </section>
  );
}
