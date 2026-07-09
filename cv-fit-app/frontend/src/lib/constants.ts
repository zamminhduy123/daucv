export interface CreditPackage {
  id: string;
  name: string;
  credits: number;
  price: number;
  formattedPrice: string;
  popular: boolean;
  tierBadge: string;
  tierBadgeBg: string;
  savingBadge: string | null;
  features: string[];
}

export const CREDIT_PACKAGES: CreditPackage[] = [ 
  {
    id: "starter",
    name: "Starter Pack",
    credits: 10,
    price: 15000,
    formattedPrice: "15.000đ",
    popular: true,
    tierBadge: "TRẢI NGHIỆM",
    tierBadgeBg: "bg-slate-100 text-slate-600",
    savingBadge: null,
    features: [
      "1.500đ / lượt",
    ],
  },
  {
    id: "mid",
    name: "Mid Pack",
    credits: 20,
    price: 24000,
    formattedPrice: "24.000đ",
    popular: false,
    tierBadge: "PHỔ BIẾN",
    tierBadgeBg: "bg-blue-50 text-blue-600",
    savingBadge: "Tiết kiệm 20%",
    features: [
      "1.250đ / lượt",
    ],
  },
  {
    id: "pro",
    name: "Pro Pack",
    credits: 50,
    price: 35000,
    formattedPrice: "35.000đ",
    popular: false,
    tierBadge: "🔥 Hời nhất",
    tierBadgeBg: "bg-red-50 text-red-600 font-bold",
    savingBadge: "Tiết kiệm 53%",
    features: [
      "700đ / lượt",
    ],
  }
];

export const GENERAL_BENEFITS = [
  {
    title: "Truy cập đầy đủ phân tích ATS",
    description: "Phân tích CV chuyên sâu với báo cáo chi tiết về điểm số và độ tương thích.",
  },
  {
    title: "Tối ưu hóa CV",
    description: "Đề xuất cải thiện CV theo từng vị trí công việc cụ thể để vượt qua vòng lọc.",
  },
  {
    title: "Phòng vấn AI 1-1",
    description: "Luyện tập với AI phỏng vấn thực tế, nhận phản hồi ngay lập tức.",
  },
  {
    title: "Job scan dựa trên CV",
    description: "Tìm kiếm các cơ hội việc làm phù hợp với hồ sơ của bạn.",
  },
  {
    title: "Tín dụng không hết hạn",
    description: "Sử dụng bất cứ lúc nào bạn cần, không giới hạn thời gian sử dụng.",
  },

  {
    title: "Không gia hạn định kỳ",
    description: "Mua một lần, dùng mãi mãi. Không có phí ẩn hay tự động gia hạn.",
  },
];
