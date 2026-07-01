import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { getAllPosts } from '@/lib/mdx';
import { ArrowLeft, Tag, FileText, BookOpen } from 'lucide-react';
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "@/components/landing/Footer";
import { BlogCTA, BlogCard } from '@/components/blog';

type Params = Promise<{ tag: string }>;

export async function generateStaticParams() {
  const posts = getAllPosts();
  const tags = new Set<string>();
  posts.forEach((post) => {
    post.tags?.forEach((tag) => tags.add(tag));
  });
  return Array.from(tags).map((tag) => ({
    tag,
  }));
}

export async function generateMetadata(props: { params: Params }): Promise<Metadata> {
  const params = await props.params;
  const posts = getAllPosts();
  const tagPosts = posts.filter((post) => post.tags?.includes(params.tag));

  if (tagPosts.length === 0) {
    return {
      title: 'Tag Not Found',
    };
  }

  return {
    title: `${params.tag} - Bài viết | Đậu Blog`,
    description: `${tagPosts.length} bài viết về ${params.tag} trên Đậu Blog.`,
    alternates: {
      canonical: `https://daucv.com/blog/tag/${params.tag}`,
    },
  };
}

export default async function TagPage(props: { params: Params }) {
  const params = await props.params;
  const posts = getAllPosts();
  const tagPosts = posts.filter((post) => post.tags?.includes(params.tag));

  if (tagPosts.length === 0) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-white">
      <LandingNavbar />

      <div className="max-w-7xl mx-auto px-6 pb-20">

        {/* Hero */}
        <section className="py-8">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-sm text-[#5A6D6D] hover:text-[var(--primary)] transition-colors mb-6"
          >
            <ArrowLeft size={16} />
            Quay lại blog
          </Link>

          <div className="flex items-center gap-3 mb-4">
            <Tag className="w-6 h-6 text-[var(--primary)]" />
            <h1 className="text-3xl md:text-4xl font-extrabold text-[#2F4F4F] font-heading">
              {params.tag}
            </h1>
          </div>

          <p className="text-gray-500 text-lg">
            {tagPosts.length} bài viết
          </p>
        </section>

        {/* Blog Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
          {tagPosts.map((post) => (
            <BlogCard key={post.slug} post={post} tag={params.tag} />
          ))}
        </div>

        {tagPosts.length === 0 && (
          <div className="text-center pb-24">
            <p className="text-gray-500">Không có bài viết nào cho tag này.</p>
          </div>
        )}

        {/* CTA */}
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
