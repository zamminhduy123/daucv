import { Gift, Coins, CalendarX, TrendingUp, UserCheck } from "lucide-react";

export default function TrustSection() {
  const points = [
    {
      icon: <Gift size={18} className="text-emerald-600" />,
      value: "Tặng 5 lượt dùng",
      label: "Khi tạo tài khoản mới",
    },
    // {
    //   icon: <Coins size={18} className="text-emerald-600" />,
    //   value: "Dùng thêm mua thêm",
    //   label: "Thanh toán linh hoạt theo nhu cầu",
    // },
    {
      icon: <CalendarX size={18} className="text-emerald-600" />,
      value: "Không phí định kỳ",
      label: "Không cần đăng ký gói tháng",
    },
    {
      icon: <TrendingUp size={18} className="text-emerald-600" />,
      value: "Tối ưu chuẩn ATS",
      label: "Nâng cấp điểm số CV tức thì",
    },
    {
      icon: <UserCheck size={18} className="text-emerald-600" />,
      value: "Phỏng vấn giả lập",
      label: "Luyện nói tự tin cùng AI",
    },
  ];

  return (
    <section className="max-w-7xl mx-auto px-4 py-10">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-0 items-center justify-center">
        {points.map((point, idx) => (
          <div
            key={idx}
            className={`flex items-center justify-center md:items-start gap-3.5 px-3 h-full ${
              idx > 0 ? "md:border-l border-[#2F4F4F]/10" : ""
            }`}
          >
            <div 
              className="shrink-0 flex items-center justify-center w-9 h-9 rounded-xl"
              style={{ backgroundColor: "rgba(16, 185, 129, 0.08)" }}
            >
              {point.icon}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-heading font-extrabold text-[#1A2D2D] text-sm md:text-[1.1rem] leading-snug tracking-tight">
                {point.value}
              </span>
              <span className="text-[10px] md:text-xs text-[#5A6D6D] mt-1 leading-snug font-medium">
                {point.label}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
