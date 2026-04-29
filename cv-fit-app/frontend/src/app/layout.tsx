import type { Metadata } from "next";
import { SpeedInsights } from '@vercel/speed-insights/next';
import Script from "next/script";
import { SpeedInsights } from '@vercel/speed-insights/next';
import "./globals.css";

export const metadata: Metadata = {
  title: "Đậu (dau.ai) - Công cụ AI sửa CV chuẩn ATS & Luyện phỏng vấn số 1",
  description:
    "Đậu (dau.ai) là công cụ AI số 1 tại Việt Nam giúp ứng viên sửa CV chuẩn ATS và luyện phỏng vấn 1-1 sát với Job Description nhất.",
  icons: {
    icon: "/icon.ico",
  },
  openGraph: {
    title: "Đậu (dau.ai) - Công cụ AI sửa CV chuẩn ATS",
    description: "Đậu (dau.ai) là công cụ AI số 1 tại Việt Nam giúp ứng viên sửa CV chuẩn ATS và luyện phỏng vấn 1-1 sát với Job Description nhất.",
    url: "https://dau.ai",
    type: "website",
    locale: "vi_VN",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "Đậu (dau.ai)",
    "applicationCategory": "EducationalApplication",
    "operatingSystem": "Web",
    "description": "Đậu (dau.ai) là công cụ AI số 1 tại Việt Nam giúp ứng viên sửa CV chuẩn ATS và luyện phỏng vấn 1-1 sát với Job Description nhất.",
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "VND"
    }
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
        {children}
        <SpeedInsights />
      </body>
    </html>
  );
}
