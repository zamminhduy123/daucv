import { getAllPosts } from '@/lib/mdx';
import { Metadata } from 'next';
import { Search, FileText } from 'lucide-react';
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "@/components/landing/Footer";
import Image from 'next/image';
import { BlogCTA } from '@/components/blog';
import BlogListClient from '@/components/blog/BlogListClient';
import { SITE_URL } from '@/lib/site';

export const metadata: Metadata = {
  title: 'Blog | Đậu CV',
  description: 'Khám phá các bài viết chia sẻ kinh nghiệm viết CV chuẩn ATS và kỹ năng phỏng vấn.',
  alternates: {
    canonical: `${SITE_URL}/blog`,
  },
};

export default function BlogIndexPage() {
  const posts = getAllPosts();

  return (
    <div className="min-h-screen bg-white">
      <LandingNavbar />

      <div className="max-w-7xl mx-auto px-6 pb-20">

        {/* 2. Hero Section */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center py-8">
          {/* Left Column */}
          <div className="h-full flex flex-col justify-start items-start gap-8">
            <div className="px-2">
              <div className="bg-green-50 text-[var(--primary)] border border-green-100 px-3 py-1.5 rounded-lg text-sm font-semibold w-fit mb-6 flex items-center gap-2">
                <FileText size={16} />
                Blog & Cẩm nang
              </div>

              <h1 className="text-3xl md:text-4xl lg:text-5xl font-extrabold text-[#2F4F4F] leading-tight mb-6 font-heading">
                Kiến thức giúp bạn<br/>thăng tiến sự nghiệp
              </h1>

              <p className="text-lg text-gray-500 mb-8 leading-relaxed mr-12">
                Bí quyết viết CV chuẩn ATS, kinh nghiệm phỏng vấn và mẹo sử dụng AI để nhận nhiều lời mời làm việc hơn.
              </p>
            </div>

            <div className="relative max-w-md">
              <Search className="text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" size={20} />
              <input
                type="text"
                id="blog-search"
                placeholder="Tìm kiếm bài viết..."
                className="w-full bg-white border border-gray-200 rounded-2xl py-4 pl-12 pr-4 text-sm focus:ring-2 focus:ring-[var(--primary)] focus:outline-none shadow-sm"
              />
            </div>
          </div>

          {/* Right Column (Mascot Placeholder) */}
          <div className="w-full aspect-[4/3] bg-gradient-to-br from-green-50 to-white rounded-[3rem] border border-green-100 flex items-center justify-center relative overflow-hidden shadow-sm">
            <div className="flex flex-col items-center gap-4 z-10">
              <Image
                src={"/blog.webp"}
                alt={""}
                fill
                className='object-cover'
              />
            </div>
          </div>
        </section>

        {/* 3. Blog List with Client-side Filtering */}
        <BlogListClient posts={posts} />

        {/* 5. Use App Banner */}
        <div className="mb-16">
          <BlogCTA
            title="Sẵn sàng có một CV chuẩn ATS?"
            description="Tạo CV chuyên nghiệp, chuẩn ATS và chinh phục nhà tuyển dụng ngay hôm nay với công cụ của Đậu."
            buttonText="Thử Ngay"
            buttonHref="/app/setup"
            image="/trophy.webp"
          />
        </div>

      </div>

      <Footer />
    </div>
  );
}
