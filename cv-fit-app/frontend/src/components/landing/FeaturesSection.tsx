import { FileCheck, Target, Wand2, MessageSquare } from 'lucide-react';
import Image from 'next/image';

/* ------------------------------------------------------------------ */
/*  FeatureCard — reusable card component                             */
/* ------------------------------------------------------------------ */

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  visual: React.ReactNode;
  bg: string;
}

function FeatureCard({ icon, title, description, visual, bg }: FeatureCardProps) {
  return (
    <div className={`${bg} rounded-3xl p-6 sm:p-8 border border-gray-100 flex flex-col min-h-[280px] sm:min-h-[300px]`}>
      {/* Header: icon + title */}
      <div className="flex items-center gap-3 mb-3">
        <div className="bg-white rounded-xl shadow-sm p-2 w-10 h-10 flex items-center justify-center flex-shrink-0">
          {icon}
        </div>
        <h3 className="text-base sm:text-lg font-bold text-[#2F4F4F]">{title}</h3>
      </div>

      {/* Description */}
      <p className="text-xs sm:text-sm text-gray-600 leading-relaxed mb-5">{description}</p>

      {/* Visual — pushed to bottom */}
      <div className="mt-auto">{visual}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Per-card visuals                                                  */
/* ------------------------------------------------------------------ */

function Card1Visual() {
  return (
    <div className="relative w-full rounded-2xl overflow-hidden shadow-sm border border-gray-100 bg-white">
      <div className="relative w-full" style={{ paddingTop: '50%' }}>
        <Image
          src="/main.webp"
          alt="CV Helper AI product preview — tối ưu CV"
          fill
          className="object-contain"
          priority
        />
      </div>
    </div>
  );
}

function Card2Visual() {
  const scores = [
    { label: 'CV Match', value: 81, color: 'bg-[#5B9144]' },
    { label: 'ATS Score', value: 88, color: 'bg-[#5B9144]' },
    { label: 'Từ khóa', value: 75, color: 'bg-yellow-400' },
  ];

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
      <p className="text-[10px] uppercase font-bold text-gray-400 mb-4 tracking-wider">Độ phù hợp tổng thể</p>
      <div className="flex items-center gap-4 mb-4">
        <div className="relative w-16 h-16 flex-shrink-0">
          <svg className="w-full h-full" viewBox="0 0 36 36">
            <path
              className="stroke-gray-100"
              strokeWidth="3"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              className="stroke-[#5B9144]"
              strokeWidth="3"
              strokeDasharray="81, 100"
              strokeLinecap="round"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-[#2F4F4F]">81%</span>
          </div>
        </div>
        <div className="flex flex-col gap-2 flex-1">
          {scores.map((s) => (
            <div key={s.label} className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-semibold text-[#2F4F4F] whitespace-nowrap">{s.label}</span>
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${s.color}`}
                  style={{ width: `${s.value}%` }}
                />
              </div>
              <span className="text-[11px] font-bold text-gray-500 w-8 text-right">{s.value}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Card3Visual() {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
      <p className="text-[10px] uppercase font-bold text-gray-400 mb-3 tracking-wider">Gợi ý chỉnh sửa</p>

      {/* Before */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[9px] uppercase font-bold text-red-400 tracking-wider">Trước</span>
        </div>
        <div className="bg-red-50/60 rounded-lg p-3 border border-red-100">
          <p className="text-[11px] text-gray-600 leading-relaxed">
            Built AI model for anomaly detection.
          </p>
        </div>
      </div>

      {/* After */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[9px] uppercase font-bold text-[#5B9144] tracking-wider">Sau</span>
        </div>
        <div className="bg-green-50/60 rounded-lg p-3 border border-green-100">
          <p className="text-[11px] text-[#2F4F4F] leading-relaxed">
            Developed a graph-based anomaly detection system with measurable model performance.
          </p>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5">
        {['rõ hơn', 'đúng keyword', 'ATS-friendly'].map((tag) => (
          <span
            key={tag}
            className="text-[9px] font-semibold bg-[var(--primary)]/10 text-[var(--primary)] px-2 py-0.5 rounded-full"
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}

function Card4Visual() {
  return (
    <div className="bg-[#F9FAF6] rounded-2xl p-4 shadow-sm border border-gray-100 relative min-h-[140px] flex items-end justify-between overflow-hidden">
      <div className="flex flex-col gap-2 flex-1 z-10">
        {/* Chat Bubble 1: Text */}
        <div className="p-3 bg-white border border-gray-100 rounded-2xl rounded-bl-none shadow-sm max-w-[160px]">
          <p className="text-[10px] text-[#2F4F4F] leading-relaxed">
            <span className="font-bold text-[var(--primary)]">Bé Đậu:</span> Bạn hãy giới thiệu về dự án đáng tự hào nhất của bạn?
          </p>
        </div>

        {/* Chat Bubble 2: Waveform */}
        <div className="p-3 bg-white border border-gray-100 rounded-2xl rounded-bl-none shadow-sm w-fit flex items-center gap-1 min-w-[100px]">
          {[2, 4, 3, 6, 4, 8, 5, 3, 6, 4, 7, 3, 2].map((h, i) => (
            <div
              key={i}
              className="w-1 bg-[var(--primary)] rounded-full"
              style={{ height: `${h * 1.5}px` }}
            />
          ))}
        </div>
      </div>

      {/* Mascot Image */}
      <div className="relative w-20 h-20 -mr-2 flex-shrink-0">
        <Image
          src="/call.webp"
          alt="Bé Đậu luyện phỏng vấn"
          fill
          className="object-contain"
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Feature data                                                      */
/* ------------------------------------------------------------------ */

const FEATURES = [
  {
    icon: <FileCheck className="text-[var(--primary)]" size={20} />,
    title: 'Tối ưu CV với AI',
    description: 'Phân tích CV và đề xuất chỉnh sửa nội dung để vượt qua ATS và phù hợp hơn với JD.',
    visual: <Card1Visual />,
    bg: 'bg-green-50/50',
  },
    {
    icon: <Wand2 className="text-purple-500" size={20} />,
    title: 'Gợi ý chỉnh sửa CV',
    description: 'Nhận đề xuất viết lại bullet point, bổ sung từ khóa và làm rõ tác động công việc.',
    visual: <Card3Visual />,
    bg: 'bg-purple-50/50',
  },
  {
    icon: <Target className="text-orange-500" size={20} />,
    title: 'Chấm điểm độ phù hợp',
    description: 'So sánh kỹ năng, kinh nghiệm và từ khóa trong CV với mô tả công việc.',
    visual: <Card2Visual />,
    bg: 'bg-orange-50/50',
  },

  {
    icon: <MessageSquare className="text-blue-500" size={20} />,
    title: 'Luyện phỏng vấn 1-1',
    description: 'Thực hành phỏng vấn cùng AI, nhận câu hỏi sát JD và phản hồi để cải thiện câu trả lời.',
    visual: <Card4Visual />,
    bg: 'bg-blue-50/50',
  },
];

/* ------------------------------------------------------------------ */
/*  Section                                                           */
/* ------------------------------------------------------------------ */

export default function FeaturesSection() {
  return (
    <section id="tính-năng" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-12">
      <div className="flex flex-col items-center justify-center mb-8">
        <h2 className="font-heading font-bold text-[#2F4F4F] text-3xl md:text-4xl mb-4">
          Đậu đồng hành với bạn mọi lúc
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Từ chỉnh sửa CV đến khi bạn nhận được offer!
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
        {FEATURES.map((f) => (
          <FeatureCard key={f.title} {...f} />
        ))}
      </div>
    </section>
  );
}
