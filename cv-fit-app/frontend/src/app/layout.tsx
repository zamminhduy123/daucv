import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CVFit — Hack Your Next Job Interview",
  description:
    "Upload your CV and job description. AI scores your fit, rewrites your resume, and runs a mock interview — built for the Vietnamese job market.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
