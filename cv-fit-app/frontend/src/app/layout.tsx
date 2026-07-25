import type { Metadata } from "next";
import { SpeedInsights } from '@vercel/speed-insights/next';
import Script from "next/script";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "Đậu - AI sửa CV chuẩn ATS & luyện phỏng vấn theo JD",
  description:
    "Tải CV và Job Description để Đậu phân tích độ phù hợp, gợi ý sửa CV chuẩn ATS, tìm kỹ năng còn thiếu và luyện phỏng vấn 1-1 bằng AI.",
  icons: {
    icon: "/icon.ico",
  },
  alternates: {
    canonical: "https://daucv.com",
  },
  openGraph: {
    title: "Đậu - AI sửa CV chuẩn ATS & luyện phỏng vấn theo JD",
    description:
      "Phân tích CV theo Job Description, kiểm tra độ phù hợp, gợi ý sửa CV chuẩn ATS và luyện phỏng vấn 1-1 bằng AI.",
    url: "https://daucv.com",
    siteName: "Đậu",
    type: "website",
    locale: "vi_VN",
  },
  twitter: {
    card: "summary_large_image",
    title: "Đậu - AI sửa CV chuẩn ATS & luyện phỏng vấn theo JD",
    description:
      "Tối ưu CV theo Job Description, kiểm tra độ phù hợp và luyện phỏng vấn 1-1 bằng AI.",
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
        "url": "https://www.daucv.com/",
        "description":
          "Tải CV và Job Description để Đậu phân tích độ phù hợp, gợi ý sửa CV chuẩn ATS, tìm kỹ năng còn thiếu và luyện phỏng vấn 1-1 bằng AI.",
      },
      {
        "@type": "WebSite",
        "url": "https://www.daucv.com/",
        "name": "Đậu",
        "publisher": {
          "@type": "Organization",
          "name": "Đậu",
        },
      },
      {
        "@type": "SoftwareApplication",
        "name": "Đậu (daucv.com)",
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Web",
        "description":
          "Tải CV và Job Description để Đậu phân tích độ phù hợp, gợi ý sửa CV chuẩn ATS, tìm kỹ năng còn thiếu và luyện phỏng vấn 1-1 bằng AI.",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "VND",
        },
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
