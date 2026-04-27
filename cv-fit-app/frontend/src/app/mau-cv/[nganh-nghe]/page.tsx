import { Metadata } from 'next';
import TemplateView from '@/components/landing/TemplateView';

import type { TemplateData } from '@/components/landing/TemplateView';

// Mock list of popular industries for Programmatic SEO
export const nganhNgheList: Record<string, TemplateData> = {
  'it-phan-mem': {
    name: "IT Phần mềm",
    title: "Mẫu CV chuẩn ATS ngành IT Phần mềm",
    subtitle: "Được tối ưu theo format mà 87% nhà tuyển dụng công nghệ tại Việt Nam đang sử dụng. Highlight technical stack, metrics, và impact thay vì chỉ liệt kê responsibilities.",
    keywords: ['Lập trình viên', 'Frontend', 'Backend', 'Fullstack', 'DevOps', 'React', 'NodeJS'],
    proTips: [
      {
        icon: "Target",
        title: "Metrics > Mô tả chung chung",
        description: "Thay vì 'Xây dựng tính năng X', hãy viết 'Xây dựng tính năng X giúp tăng 40% conversion rate và giảm 25% load time'. Recruiter IT muốn thấy impact cụ thể."
      },
      {
        icon: "Zap",
        title: "Tech Stack phải đứng trước",
        description: "Đưa Skills section lên ngay sau Summary. Hầu hết ATS và recruiter scan qua tech stack trong 10 giây đầu tiên. Nếu match → đọc tiếp. Nếu không → next."
      },
      {
        icon: "TrendingUp",
        title: "Side projects = hiring signal mạnh",
        description: "Nếu bạn có GitHub, personal blog, hoặc open-source contribution → đặt link ngay dưới Contact. Với IT, 'Learn by doing' culture rất được trọng."
      },
      {
        icon: "Sparkles",
        title: "ATS-friendly = No fancy design",
        description: "CV 2 cột, icon hoa lá hẹ, font chữ lạ → ATS đọc sai hoặc bỏ qua. Stick with single-column, standard fonts (Arial, Calibri), và heading rõ ràng."
      }
    ],
    template: {
      name: "NGUYỄN VĂN A",
      title: "Senior Full-Stack Developer",
      contact: "📧 nguyenvana@email.com | 📱 0901234567 | 🔗 linkedin.com/in/nguyenvana | 💻 github.com/nguyenvana",
      summary: "Full-Stack Developer với 5+ năm kinh nghiệm phát triển web applications sử dụng React, Node.js, và cloud infrastructure. Đã lead 3 projects với team size 5-8 người, giúp tăng 45% performance và giảm 30% infrastructure cost cho platform có 100K+ daily active users.",
      experience: [
        {
          role: "Senior Full-Stack Developer",
          company: "Tech Startup XYZ",
          period: "03/2022 - Hiện tại",
          achievements: [
            "Lead team 6 engineers phát triển microservices architecture, giảm deployment time từ 2h xuống 15 phút",
            "Optimize database queries và caching strategy, cải thiện API response time 60% (từ 800ms → 320ms)",
            "Implement CI/CD pipeline với Docker & Kubernetes, tăng deployment frequency từ 2 lần/tuần lên 5 lần/ngày"
          ]
        },
        {
          role: "Full-Stack Developer",
          company: "Agency ABC",
          period: "06/2020 - 02/2022",
          achievements: [
            "Xây dựng e-commerce platform phục vụ 50K+ users, xử lý 10K+ transactions/tháng",
            "Integrate payment gateways (VNPay, Momo, Zalopay) và shipping APIs",
            "Refactor legacy codebase từ jQuery sang React, giảm bug rate 40%"
          ]
        }
      ],
      education: "🎓 Cử nhân Khoa học Máy tính - Đại học Bách Khoa TP.HCM (2016-2020) | GPA: 3.6/4.0",
      skills: [
        "Frontend: React, TypeScript, Next.js, Tailwind CSS",
        "Backend: Node.js, Express, NestJS, GraphQL",
        "Database: PostgreSQL, MongoDB, Redis",
        "DevOps: Docker, Kubernetes, AWS (EC2, S3, Lambda), CI/CD",
        "Tools: Git, Jira, Figma, Postman"
      ]
    }
  },
  'marketing': {
    name: "Marketing",
    title: "Mẫu CV chuẩn ATS ngành Marketing / Truyền thông",
    subtitle: "Được thiết kế để phô diễn Data, Creativity, và ROI. Format chuẩn xác giúp vượt qua vòng quét từ khóa ATS.",
    keywords: ['Digital Marketing', 'Content Writer', 'SEO', 'Performance Marketing', 'Brand Manager'],
    proTips: [
      {
        icon: "Target",
        title: "Tập trung vào ROI & Conversion",
        description: "Marketters giỏi là người mang lại doanh thu. Đừng viết 'Chạy Ads Facebook'. Hãy viết 'Quản lý ngân sách 200tr/tháng, CPL giảm 30% sau 2 tuần optimize'."
      },
      {
        icon: "TrendingUp",
        title: "Kèm Link Portfolio trực quan",
        description: "Bắt buộc phải có Portfolio (Notion, PDF) đính kèm phần Contact. Trăm nghe không bằng một thấy."
      },
      {
        icon: "Sparkles",
        title: "Dùng Action Verbs mạnh",
        description: "Bắt đầu các đầu việc bằng: 'Dẫn dắt', 'Lan tỏa', 'Tăng trưởng', thay vì 'Được giao nhiệm vụ'."
      }
    ],
    template: {
      name: "NGUYỄN THỊ B",
      title: "Performance Marketing Specialist",
      contact: "📧 nguyenthib@email.com | 📱 0901234567 | 🔗 behance.net/nguyenthib",
      summary: "3 năm kinh nghiệm trong Performance Marketing & Growth Hacking. Chuyên môn hóa tối ưu hóa tỷ lệ chuyển đổi (CRO) và Data Analysis. Đã từng quản lý trực tiếp campaign lớn với ROI đạt mức 350%.",
      experience: [
        {
          role: "Performance Marketing Executive",
          company: "Agency Marketing XYZ",
          period: "03/2021 - Hiện tại",
          achievements: [
            "Tối ưu hóa phễu chuyển đổi giúp giảm chi phí CPA 40% trong vòng 1 tháng",
            "Thiết kế lại luồng Email Marketing tăng tỷ lệ Open Rate từ 15% lên 32%"
          ]
        }
      ],
      education: "🎓 Cử nhân Marketing - Đại học Kinh tế TP.HCM | GPA: 3.8/4.0",
      skills: [
        "Chuyên môn: Performance Marketing, SEO, Content Strategy",
        "Công cụ: Facebook Ads, Google Ads Manager, Google Analytics, Data Studio"
      ]
    }
  },
  'nhan-su-hr': {
    name: "Nhân sự",
    title: "Mẫu CV chuẩn ATS ngành Hành chính Nhân sự (HR)",
    subtitle: "Ghi điểm ngay lập tức với người trong nghề bằng văn phong chuyên môn sâu và số liệu quản lý.",
    keywords: ['Tuyển dụng', 'C&B', 'Đào tạo', 'L&D', 'Nhân sự', 'Talent Acquisition'],
    proTips: [
      {
        icon: "Target",
        title: "Số liệu tuyển dụng cụ thể",
        description: "Ghi rõ số lượng nhân sự đã tuyển thành công, time-to-fill và retention rate. Đó là KPI quan trọng nhất của HR."
      },
      {
        icon: "TrendingUp",
        title: "Sử dụng từ vựng cấu trúc",
        description: "Dùng các thuật ngữ ATS, C&B, L&D rõ ràng. Người đọc CV của bạn chính là đồng nghiệp tương lai."
      },
      {
        icon: "Zap",
        title: "Văn hóa công ty & Khả năng xử lý vấn đề",
        description: "Nhấn mạnh những hoạt động xây dựng văn hóa công ty bạn đã tổ chức để cho thấy cái 'tâm' với nghề."
      }
    ],
    template: {
      name: "TRẦN VĂN C",
      title: "Senior Talent Acquisition",
      contact: "📧 tranvanc@email.com | 📱 0901234567 | 🔗 linkedin.com/in/tranvanc",
      summary: "Chuyên viên tuyển dụng với 4 năm kinh nghiệm mảng Tech & Product. Có khả năng xây dựng Employer Branding và thiết lập quy trình tuyển dụng từ con số 0.",
      experience: [
        {
          role: "Talent Acquisition Specialist",
          company: "Tech Startup MNO",
          period: "05/2021 - Hiện tại",
          achievements: [
            "Tuyển dụng thành công 40+ vị trí Senior Tech trong 6 tháng, giảm 20% chi phí Headhunting",
            "Tổ chức thành công 3 sự kiện Job Fair có quy mô 500+ sinh viên"
          ]
        }
      ],
      education: "🎓 Cử nhân Quản trị Nhân sự - Đại học Lao động Xã hội | GPA: 3.5/4.0",
      skills: [
        "Nghiệp vụ: Tuyển dụng (Tech recruitment), Onboarding, Employer Branding",
        "Công cụ: Base HRM, BambooHR, LinkedIn Recruiter"
      ]
    }
  }
};

// 1. DYNAMIC METADATA: Extremely important for pSEO!
export async function generateMetadata({ params }: { params: Promise<{ 'nganh-nghe': string }> }): Promise<Metadata> {
  const awaitedParams = await params;
  const nganhNghe = awaitedParams['nganh-nghe'];
  
  // Fallback to generic if industry isn't in our mock list
  const data = nganhNgheList[nganhNghe as keyof typeof nganhNgheList];
  if (!data) {
    return {
      title: `Cách viết CV ngành ${nganhNghe || ''} chuẩn ATS | Đậu (dau.ai)`,
      description: `Hướng dẫn cách viết CV ngành ${nganhNghe || ''} chuyên nghiệp để vượt qua vòng lọc hồ sơ ATS. AI của Đậu giúp bạn tối ưu CV chuẩn nhất.`,
    };
  }

  return {
    title: `${data.title} chuẩn ATS 2026 | Đậu (dau.ai)`,
    description: `Tải xuống ${data.title} và xem hướng dẫn chi tiết cách viết CV chuyên nghiệp để vượt qua vòng lọc hồ sơ ATS. Công cụ AI sửa CV hoàn toàn tự động.`,
    keywords: data.keywords.join(", ")
  };
}


// 2. PAGE COMPONENT
export default async function MauCvPage({ params }: { params: Promise<{ 'nganh-nghe': string }> }) {
  const awaitedParams = await params;
  const nganhNghe = awaitedParams['nganh-nghe'];
  
  // Use mock data fallback for the template view
  const data = (nganhNghe && nganhNgheList[nganhNghe as keyof typeof nganhNgheList]) || {
    title: `Mẫu CV ngành ${nganhNghe ? nganhNghe.replace(/-/g, ' ') : 'Chuyên nghiệp'}`,
    name: nganhNghe ? nganhNghe.replace(/-/g, ' ') : 'Chuyên nghiệp',
    subtitle: "Được tối ưu theo format mà hầu hết nhà tuyển dụng tại Việt Nam đang sử dụng. Highlight technical stack, metrics, và impact thay vì chỉ liệt kê responsibilities.",
    keywords: ['CV', 'Cách viết CV', 'Tuyển dụng', 'Cơ hội việc làm'],
    proTips: [
      {
        icon: 'Target',
        title: 'Đọc thật kỹ Job Description',
        description: 'Đọc thật kỹ Job Description (Mô tả công việc) của nhà tuyển dụng.'
      },
      {
        icon: 'Zap',
        title: 'Dùng từ khóa chuyên ngành',
        description: 'Dùng chính các từ vựng chuyên ngành trong JD để viết vào CV của bạn.'
      },
      {
        icon: 'TrendingUp',
        title: 'Định lượng thành tựu',
        description: 'Luôn cố gắng định lượng thành tựu bằng những con số cụ thể.'
      }
    ],
    template: {
      name: "NGUYỄN VĂN A",
      title: "Chuyên viên có kinh nghiệm",
      contact: "📧 nguyenvana@email.com | 📱 0901234567 | 🔗 linkedin.com/in/nguyenvana",
      summary: "Nhân sự với 5+ năm kinh nghiệm. Đã lead nhiều dự án, giúp tăng 45% kết quả kinh doanh.",
      experience: [
        {
          role: "Chuyên viên cấp cao",
          company: "Công ty TNHH XYZ",
          period: "03/2022 - Hiện tại",
          achievements: [
            "Đóng góp chính vào sự thành công của dự án, vượt KPI 20%",
            "Tối ưu hóa quy trình giúp tiết kiệm 30% thời gian"
          ]
        }
      ],
      education: "🎓 Cử nhân Đại học - Bằng Giỏi | GPA: 3.6/4.0",
      skills: [
        "Kỹ năng mềm: Giao tiếp, làm việc nhóm, quản lý thời gian",
        "Kỹ năng cứng: Các phần mềm và công cụ chuyên ngành"
      ]
    }
  };

  return <TemplateView data={data} />;
}
