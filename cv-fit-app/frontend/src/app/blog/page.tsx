import { getAllPosts } from '@/lib/mdx';
import Link from 'next/link';
import { Metadata } from 'next';
import { Clock, Search, CalendarArrowDown, FileText, Smile, Leaf, Mail } from 'lucide-react';
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "@/components/landing/Footer";
import Image from 'next/image';

export const metadata: Metadata = {
  title: 'Blog | Đậu CV',
  description: 'Khám phá các bài viết chia sẻ kinh nghiệm viết CV chuẩn ATS và kỹ năng phỏng vấn.',
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
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center pt-8 pb-16">
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
            <div className="flex items-center gap-6 flex-wrap w-full no-scrollbar pb-2 md:pb-0">
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
          </div>
          
          {/* Right Column (Mascot Placeholder) */}
          <div className="w-full aspect-[4/3] bg-gradient-to-br from-green-50 to-white rounded-[3rem] border border-green-100 flex items-center justify-center relative overflow-hidden shadow-sm">
            <div className="absolute top-10 left-10 w-16 h-16 bg-green-200/50 rounded-full blur-xl animate-pulse"></div>
            <div className="absolute bottom-10 right-10 w-24 h-24 bg-yellow-200/40 rounded-full blur-2xl animate-pulse delay-700"></div>
            <div className="absolute top-1/4 right-1/4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-yellow-400/60 animate-bounce">
                <path d="M12 2L15 9L22 12L15 15L12 22L9 15L2 12L9 9L12 2Z" fill="currentColor" />
              </svg>
            </div>
            
            <div className="flex flex-col items-center gap-4 z-10">
              <Smile size={80} className="text-[var(--primary)]/20" />
              <p className="text-[var(--primary)]/40 font-bold font-heading text-xl">Mascot Illustration Here</p>
            </div>
          </div>
        </section>

        <div className="border-b border-gray-100 mb-12" />

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

        {/* 5. Newsletter Section */}
        <section className="bg-gradient-to-r from-green-50 to-[#F9F9F2] rounded-[3rem] p-10 md:p-12 border border-green-100 flex flex-col md:flex-row items-center justify-between gap-10 shadow-sm relative overflow-hidden">
          <div className="absolute -left-10 -bottom-10 opacity-30">
            <Leaf size={160} className="text-[var(--primary)]" />
          </div>
          
          <div className="flex-1 relative z-10 text-center md:text-left">
            <h3 className="text-2xl md:text-3xl font-bold text-[#2F4F4F] font-heading mb-3">
              Đón đầu xu hướng nghề nghiệp
            </h3>
            <p className="text-gray-500 text-sm md:text-base">
              Nhận mẹo viết CV, kỹ năng phỏng vấn và thông tin mới nhất gửi trực tiếp vào hộp thư của bạn.
            </p>
          </div>
          
          <div className="w-full md:w-auto relative z-10">
            <div className="flex flex-col sm:flex-row items-center bg-white p-1.5 rounded-2xl border border-gray-200 shadow-sm gap-2">
              <div className="flex items-center pl-3 text-gray-400 flex-1 w-full">
                <Mail size={18} />
                <input 
                  type="email" 
                  placeholder="Nhập email của bạn..." 
                  className="w-full bg-transparent border-none focus:ring-0 text-sm px-3 py-2 outline-none"
                />
              </div>
              <button className="w-full sm:w-auto bg-[var(--primary)] hover:bg-[#4a8233] text-white px-6 py-2.5 rounded-xl text-sm font-bold transition-colors shadow-sm">
                Đăng ký
              </button>
            </div>
            <p className="text-[10px] text-gray-400 text-center md:text-left mt-3">
              Không spam. Bạn có thể hủy đăng ký bất cứ lúc nào.
            </p>
          </div>
        </section>

        {/* 6. Pagination */}
        <div className="flex items-center justify-center gap-2 mt-16 mb-8">
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
        </div>

      </div>
      
      <Footer />
    </div>
  );
}
