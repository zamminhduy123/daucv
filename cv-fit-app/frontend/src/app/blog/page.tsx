import { getAllPosts } from '@/lib/mdx';
import Link from 'next/link';
import { Metadata } from 'next';
import { Clock, Search, CalendarArrowDown, FileText, Smile, Leaf, Mail } from 'lucide-react';
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "@/components/landing/Footer";
import Image from 'next/image';
import { BlogCTA } from '@/components/blog';

export const metadata: Metadata = {
  title: 'Blog | Đậu CV',
  description: 'Khám phá các bài viết chia sẻ kinh nghiệm viết CV chuẩn ATS và kỹ năng phỏng vấn.',
  alternates: {
    canonical: 'https://daucv.com/blog',
  },
};

export default function BlogIndexPage() {
  const posts = getAllPosts();

  const categories = [
    { name: "Tất cả", active: true },
    { name: "CV & Resumes", active: false },
    { name: "Kinh nghiệm Phỏng vấn", active: false },
    { name: "Tìm việc", active: false },
    { name: "Thăng tiến", active: false },
    { name: "Sản phẩm mới", active: false },
  ];

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
            
            {/* <div className="relative max-w-md">
              <Search className="text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" size={20} />
              <input 
                type="text" 
                placeholder="Tìm kiếm bài viết..." 
                className="w-full bg-white border border-gray-200 rounded-2xl py-4 pl-12 pr-4 text-sm focus:ring-2 focus:ring-[var(--primary)] focus:outline-none shadow-sm"
              />
            </div> */}
            {/* Left: Filters */}
            
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

        <div className="flex items-center gap-6 flex-wrap w-full no-scrollbar pb-2 my-4">
              {categories.map((cat, idx) => (
                <div 
                  key={idx}
                  className={
                    cat.active 
                      ? "bg-green-50 text-[var(--primary)] px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap"
                      : "text-gray-500 hover:text-[#2F4F4F] font-medium text-sm whitespace-nowrap cursor-pointer px-2 py-2 transition-colors"
                  }
                >
                  {cat.name}
                </div>
              ))}
            </div>

        {/* <div className="border-b border-gray-100 mb-12" /> */}

        {/* 4. Blog Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
          {posts.map((post) => (
            <Link key={post.slug} href={`/blog/${post.slug}`} className="group block h-full">
              <article className="bg-white p-4 rounded-[2rem] border border-gray-100 shadow-sm hover:shadow-md transition-shadow group flex flex-col h-full cursor-pointer">
                
                {/* Image Area */}
                <div className="w-full h-48 rounded-2xl flex items-center justify-center mb-6 relative overflow-hidden bg-gray-50">
                  <img 
                    src={post.coverImage} 
                    alt={post.title}
                    className="group-hover:scale-105 transition-transform duration-500 object-cover w-full h-full"
                  />
                </div>

                {/* Content Area */}
                <div className="flex flex-col flex-grow px-2">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-green-50 text-[var(--primary)]">
                      {post.category}
                    </span>
                    <span className="flex items-center gap-1.5 text-xs text-gray-400 font-medium">
                      <Clock size={12} />
                      {post.readTime}
                    </span>
                  </div>
                  
                  <h2 className="text-xl font-bold text-[#2F4F4F] mb-3 leading-snug group-hover:text-[var(--primary)] transition-colors font-heading">
                    {post.title}
                  </h2>
                  
                  <p className="text-gray-500 text-sm leading-relaxed mb-6 line-clamp-2">
                    {post.description}
                  </p>

                  {/* Footer */}
                  <div className="mt-auto flex items-center justify-between pt-4">
                    <div className="flex items-center gap-2">
                      <img 
                        src={post.authorAvatar} 
                        alt={post.author} 
                        className="w-6 h-6 rounded-full bg-green-100 object-cover" 
                      />
                      <span className="text-xs font-bold text-[#2F4F4F]">
                        {post.author}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400 font-medium">
                      {post.date}
                    </span>
                  </div>
                </div>
                
              </article>
            </Link>
          ))}
        </div>

        
        
        {posts.length === 0 && (
          <div className="text-center pb-24">
            <p className="text-gray-500">Hiện tại chưa có bài viết nào. Xin vui lòng quay lại sau!</p>
          </div>
        )}

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

        {/* 6. Pagination */}
        {/* <div className="flex items-center justify-center gap-2 mt-16 mb-8">
          <button className="flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-[#2F4F4F] px-3 py-2 transition-colors">
            &lsaquo; Trước
          </button>
          <button className="w-8 h-8 flex items-center justify-center rounded-lg bg-green-50 text-[var(--primary)] text-sm font-bold">
            1
          </button>
          <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-600 text-sm font-medium transition-colors">
            2
          </button>
          <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-600 text-sm font-medium transition-colors">
            3
          </button>
          <span className="text-gray-400">...</span>
          <button className="flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-[#2F4F4F] px-3 py-2 transition-colors">
            Tiếp &rsaquo;
          </button>
        </div> */}

      </div>
      
      <Footer />
    </div>
  );
}
