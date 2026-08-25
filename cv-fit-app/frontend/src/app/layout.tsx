import type { Metadata } from "next";
import { SpeedInsights } from '@vercel/speed-insights/next';
import Script from "next/script";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { SITE_URL } from '@/lib/site';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Đậu - AI sửa CV chuẩn ATS & luyện phỏng vấn theo JD",
  description:
    "Tải CV và Job Description để Đậu phân tích độ phù hợp, gợi ý sửa CV chuẩn ATS, tìm kỹ năng còn thiếu và luyện phỏng vấn 1-1 bằng AI.",
  icons: {
    icon: "/icon.ico",
  },
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    title: "Đậu - AI sửa CV chuẩn ATS & luyện phỏng vấn theo JD",
    description:
      "Phân tích CV theo Job Description, kiểm tra độ phù hợp, gợi ý sửa CV chuẩn ATS và luyện phỏng vấn 1-1 bằng AI.",
    url: SITE_URL,
    siteName: "Đậu",
    locale: "vi_VN",
    type: "website",
    images: [
      {
        url: `${SITE_URL}/og-image.jpg`,
        width: 1200,
        height: 630,
        alt: "Đậu - AI sửa CV chuẩn ATS & luyện phỏng vấn theo JD",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Đậu - AI sửa CV chuẩn ATS & luyện phỏng vấn theo JD",
    description:
      "Tối ưu CV theo Job Description, kiểm tra độ phù hợp và luyện phỏng vấn 1-1 bằng AI.",
    images: [`${SITE_URL}/og-image.jpg`],
  },
};

import { Providers } from "@/context/Providers";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "name": "Đậu",
        "url": `${SITE_URL}/`,
        "logo": `${SITE_URL}/apple-icon.png`,
        "description":
          "Tải CV và Job Description để Đậu phân tích độ phù hợp, gợi ý sửa CV chuẩn ATS, tìm kỹ năng còn thiếu và luyện phỏng vấn 1-1 bằng AI.",
      },
      {
        "@type": "WebSite",
        "url": `${SITE_URL}/`,
        "name": "Đậu",
        "publisher": {
          "@type": "Organization",
          "name": "Đậu",
        },
      },
      {
        "@type": "SoftwareApplication",
        "name": "Đậu — AI Sửa CV Chuẩn ATS & Luyện Phỏng Vấn",
        "url": `${SITE_URL}/`,
        "applicationCategory": "BusinessApplication",
        "applicationSubCategory": "CareerApplication",
        "operatingSystem": "Web",
        "description":
          "Tải CV và Job Description để Đậu phân tích độ phù hợp, gợi ý sửa CV chuẩn ATS, tìm kỹ năng còn thiếu và luyện phỏng vấn 1-1 bằng AI.",
        "featureList": [
          "Chấm điểm khớp CV & JD (ATS Match Score)",
          "Phát hiện từ khóa và kỹ năng còn thiếu theo yêu cầu tuyển dụng",
          "Tối ưu và viết lại nội dung CV chuẩn ATS",
          "Luyện phỏng vấn thử 1-1 bằng giọng nói AI tương tác hai chiều"
        ],
        "offers": [
          {
            "@type": "Offer",
            "name": "Starter Pack",
            "price": "15000",
            "priceCurrency": "VND",
            "description": "10 credits phân tích CV và luyện phỏng vấn AI"
          },
          {
            "@type": "Offer",
            "name": "Mid Pack",
            "price": "24000",
            "priceCurrency": "VND",
            "description": "20 credits phân tích CV và luyện phỏng vấn AI"
          },
          {
            "@type": "Offer",
            "name": "Pro Pack",
            "price": "35000",
            "priceCurrency": "VND",
            "description": "50 credits phân tích CV và luyện phỏng vấn AI"
          }
        ],
      },
    ],
  };

  return (
    <html lang="vi">
      <head>
        <Script
          async
          src="https://www.googletagmanager.com/gtag/js?id=G-PD8LM96EWZ"
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());

            gtag('config', 'G-PD8LM96EWZ');
          `}
        </Script>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body>
        <Providers>
          {children}
          <Toaster />
          <SpeedInsights />
        </Providers>
      </body>
    </html>
  );
}
