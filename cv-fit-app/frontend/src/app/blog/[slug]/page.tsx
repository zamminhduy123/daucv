import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { MDXRemote } from 'next-mdx-remote/rsc';
import { getPostBySlug, getAllPosts, type OmitBlogPost } from '@/lib/mdx';
import Link from 'next/link';
import {
  ChevronRight, ChevronLeft, Calendar, Clock, Share2, Mail,
  Link as LinkIcon, CheckCircle2, ArrowRight, MessageSquare,
  List, BookOpen, Sparkles
} from 'lucide-react';
import { LandingNavbar } from "@/components/shared/TopNavbar";
import Footer from "@/components/landing/Footer";
import { BlogTOC } from "@/components/shared/BlogTOC";
import { SITE_URL } from '@/lib/site';
import { 
  BlogMeta, BlogHero, TakeawaysBox, FeatureGrid, 
  StepList, ChecklistSection, BlogCTA, CommentsSection, BlogContentLayout 
} from "@/components/blog";

const FALLBACK_OG_IMAGE = '/trophy.webp';

type Params = Promise<{ slug: string }>;

export async function generateStaticParams() {
  const posts = getAllPosts();
  return posts.map((post) => ({
    slug: post.slug,
  }));
}

export async function generateMetadata(props: { params: Params }): Promise<Metadata> {
  const params = await props.params;
  try {
    const post = getPostBySlug(params.slug);
    const ogImage = post.coverImage || FALLBACK_OG_IMAGE;
    return {
      title: `${post.title} | Đậu Blog`,
      description: post.description,
      keywords: post.tags,
      alternates: {
        canonical: `${SITE_URL}/blog/${params.slug}`,
      },
      openGraph: {
        title: post.title,
        description: post.description,
        url: `${SITE_URL}/blog/${params.slug}`,
        type: 'article',
        publishedTime: post.date,
        tags: post.tags,
        images: [
          {
            url: ogImage,
            alt: post.title,
            width: 1200,
            height: 630,
          },
        ],
      },
      twitter: {
        card: 'summary_large_image',
        title: post.title,
        description: post.description,
        images: [ogImage],
      },
    };
  } catch (error) {
    return {
      title: 'Post Not Found',
    };
  }
}

function getTextFromChildren(children: any): string {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) return children.map(getTextFromChildren).join('');
  if (children?.props?.children) return getTextFromChildren(children.props.children);
  return '';
}

const mdxComponents = {
  h2: (props: any) => {
    const text = getTextFromChildren(props.children);
    const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return <h2 id={id} {...props} />;
  },
  h3: (props: any) => {
    const text = getTextFromChildren(props.children);
    const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return <h3 id={id} {...props} />;
  },
  BlogMeta,
  BlogHero,
  TakeawaysBox,
  FeatureGrid,
  StepList,
  ChecklistSection,
  BlogCTA,
  CommentsSection,
  BlogContentLayout,
};

function extractHeadings(content: string) {
  const headings: { level: number; text: string; id: string }[] = [];
  const regex = /^(##?#?)\s+(.+)$/gm;
  let match;
  while ((match = regex.exec(content)) !== null) {
    const level = match[1].length;
    // Remove markdown links/boldness from text
    const text = match[2].replace(/\[(.*?)\]\(.*?\)/g, '$1').replace(/[*_~`]/g, '');
    const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    headings.push({ level, text, id });
  }
  return headings;
}

export default async function BlogPostPage(props: { params: Params }) {
  const params = await props.params;
  
  try {
    const post = getPostBySlug(params.slug);
    const allPosts = getAllPosts();
    const sortedPosts = [...allPosts].sort((a, b) => (a.date < b.date ? -1 : 1));

    // Use frontmatter prevSlug/nextSlug if available, fallback to sorted order
    let prevPost = null;
    let nextPost = null;
    if ('prevSlug' in post) {
      const prevSlug = (post as any).prevSlug;
      const nextSlug = (post as any).nextSlug;
      if (prevSlug && prevSlug !== 'null') {
        prevPost = allPosts.find(p => p.slug === prevSlug);
      }
      if (nextSlug && nextSlug !== 'null') {
        nextPost = allPosts.find(p => p.slug === nextSlug);
      }
    }
    if (!prevPost) {
      const idx = sortedPosts.findIndex(p => p.slug === post.slug);
      if (idx > 0) prevPost = sortedPosts[idx - 1];
    }
    if (!nextPost) {
      const idx = sortedPosts.findIndex(p => p.slug === post.slug);
      if (idx < sortedPosts.length - 1) nextPost = sortedPosts[idx + 1];
    }
    type PostWithSharedTags = OmitBlogPost & { sharedTags: string[] };
    const sharedTagPosts = sortedPosts
      .filter(p => p.slug !== post.slug)
      .map((p): PostWithSharedTags => ({
        ...p,
        sharedTags: p.tags.filter(t => post.tags.includes(t)),
      }))
      .filter((p): p is PostWithSharedTags => p.sharedTags.length > 0)
      .sort((a, b) => b.sharedTags.length - a.sharedTags.length)
      .slice(0, 3);
    const fallbackPosts: PostWithSharedTags[] = allPosts
      .filter(p => p.slug !== post.slug)
      .slice(0, 3)
      .map(p => ({ ...p, sharedTags: [] }));
    const relatedPosts: PostWithSharedTags[] = sharedTagPosts.length > 0
      ? sharedTagPosts
      : fallbackPosts;
    const headings = extractHeadings(post.content);

    const jsonLd = {
      "@context": "https://schema.org",
      "@type": "BlogPosting",
      "headline": post.title,
      "description": post.description,
      "image": post.coverImage,
      "datePublished": post.date,
      "author": {
        "@type": "Person",
        "name": post.author,
      },
      "publisher": {
        "@type": "Organization",
        "name": "Đậu CV",
        "logo": {
          "@type": "ImageObject",
          "url": `${SITE_URL}/main-icon.webp`
        }
      },
      "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": `${SITE_URL}/blog/${post.slug}`
      }
    };

    const breadcrumbJsonLd = {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "name": "Trang chủ",
          "item": SITE_URL,
        },
        {
          "@type": "ListItem",
          "position": 2,
          "name": "Blog",
          "item": `${SITE_URL}/blog`,
        },
        {
          "@type": "ListItem",
          "position": 3,
          "name": post.title,
          "item": `${SITE_URL}/blog/${post.slug}`,
        },
      ],
    };

    return (
      <div className="min-h-screen bg-[#F9F9F2]">
        {/* Structured Data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
        />
        <LandingNavbar />
        
        <div className="max-w-[1200px] mx-auto py-12 px-6">          
          <div className="flex flex-col lg:flex-row gap-12">
            {/* Main Content Area (Left) */}
            <main className="flex-1 lg:max-w-[800px] w-full">
              {/* Category Tag */}
              <div className="mb-4">
                <span className="inline-block bg-[#E8F5E9] text-[#2E7D32] px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase">
                  {post.category}
                </span>
              </div>

              {/* Title & Metadata */}
              <h1 className="text-3xl md:text-5xl font-extrabold text-[#2F4F4F] font-heading mb-6 leading-tight">
                {post.title}
              </h1>
              
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#2F4F4F]/10 pb-6 mb-8">
                 <div className="flex items-center gap-6 text-sm text-[#5A6D6D]">
                   <div className="flex items-center gap-2">
                     <img src={post.authorAvatar} alt={post.author} className="w-8 h-8 rounded-full bg-gray-200" />
                     <span className="font-medium text-[#2F4F4F]">{post.author}</span>
                   </div>
                   <div className="flex items-center gap-1.5">
                     <Calendar className="w-4 h-4 text-[var(--primary)]" />
                     <time dateTime={post.date}>{post.date}</time>
                   </div>
                   <div className="flex items-center gap-1.5">
                     <Clock className="w-4 h-4 text-[var(--primary)]" />
                     <span>{post.readTime}</span>
                   </div>
                 </div>
                 
                 {/* Share Icons */}
                 <div className="flex items-center gap-3">
                    <button className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500 hover:text-[var(--primary)] hover:border-[var(--primary)] transition-colors shadow-sm">
                      <Share2 className="w-4 h-4" />
                    </button>
                    <button className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500 hover:text-[var(--primary)] hover:border-[var(--primary)] transition-colors shadow-sm">
                      <Mail className="w-4 h-4" />
                    </button>
                    <button className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500 hover:text-[var(--primary)] hover:border-[var(--primary)] transition-colors shadow-sm">
                      <LinkIcon className="w-4 h-4" />
                    </button>
                 </div>
              </div>

              {/* Intro/Summary */}
              {/* <p className="text-xl text-gray-600 leading-relaxed mb-8 font-medium">
                {post.description}
              </p> */}

              {/* Hero Image */}
              <div className="relative w-full aspect-video rounded-3xl overflow-hidden mb-12 shadow-sm">
                <img src={post.coverImage} alt={post.title} className="w-full h-full object-cover" />
              </div>

              {/* What You'll Learn Box */}
              {/* {headings.length > 0 && (
                <div className="bg-[#E8F5E9]/50 border border-[#2E7D32]/20 rounded-2xl p-6 md:p-8 mb-10">
                  <h3 className="text-xl font-bold text-[#2F4F4F] mb-4 flex items-center gap-2">
                    <CheckCircle2 className="w-6 h-6 text-[#2E7D32]" />
                    Nội dung chính bạn sẽ tìm hiểu
                  </h3>
                  <ul className="space-y-3">
                    {headings.filter(h => h.level === 2).map((heading, i) => (
                      <li key={i} className="flex items-start gap-3 text-gray-700">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#2E7D32] mt-2.5 flex-shrink-0" />
                        <span className="font-medium">{heading.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )} */}

              {/* Content */}
              <article className="prose prose-lg prose-green max-w-none 
                prose-headings:font-heading prose-headings:text-[#2F4F4F] 
                prose-h2:text-3xl prose-h2:mt-12 prose-h2:mb-6 prose-h2:border-b prose-h2:border-gray-100 prose-h2:pb-4
                prose-h3:text-2xl prose-h3:mt-8 prose-h3:mb-4
                prose-p:text-gray-700 prose-p:leading-relaxed
                prose-a:text-[var(--primary)] prose-a:font-medium prose-a:no-underline hover:prose-a:underline
                prose-strong:text-[#2F4F4F] 
                prose-ul:text-gray-700 prose-ol:text-gray-700
                prose-li:my-2
                prose-img:rounded-2xl prose-img:shadow-sm
                prose-blockquote:border-l-4 prose-blockquote:border-[var(--primary)] prose-blockquote:bg-[#F9F9F2] prose-blockquote:py-2 prose-blockquote:px-6 prose-blockquote:rounded-r-xl prose-blockquote:not-italic prose-blockquote:text-gray-700
                bg-white p-8 md:p-12 rounded-3xl shadow-sm border border-[#2F4F4F]/5">
                <MDXRemote source={post.content} components={mdxComponents} />
              </article>

              {/* Prev/Next Post Navigation */}
              <nav className="mt-12 grid grid-cols-2 gap-4">
                {prevPost && (
                  <Link href={`/blog/${prevPost.slug}`} className="group flex flex-col gap-1 p-4 bg-white rounded-2xl border border-[#2F4F4F]/5 hover:border-[var(--primary)]/30 transition-colors">
                    <div className="flex items-center gap-1 text-xs text-[#5A6D6D]">
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Bài viết trước</span>
                    </div>
                    <span className="text-sm font-semibold text-[#2F4F4F] group-hover:text-[var(--primary)] transition-colors line-clamp-2">
                      {prevPost.title}
                    </span>
                  </Link>
                )}
                {nextPost && (
                  <Link href={`/blog/${nextPost.slug}`} className="group flex flex-col gap-1 p-4 bg-white rounded-2xl border border-[#2F4F4F]/5 hover:border-[var(--primary)]/30 transition-colors text-right">
                    <div className="flex items-center justify-end gap-1 text-xs text-[#5A6D6D]">
                      <span>Bài viết tiếp theo</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-sm font-semibold text-[#2F4F4F] group-hover:text-[var(--primary)] transition-colors line-clamp-2">
                      {nextPost.title}
                    </span>
                  </Link>
                )}
              </nav>

              {/* CTA Banner */}
              {/* <div className="mt-12 bg-gradient-to-br from-[#2E7D32] to-[#1B5E20] rounded-3xl p-8 md:p-12 text-center text-white shadow-lg relative overflow-hidden">
                <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-white/10 rounded-full blur-2xl" />
                <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-40 h-40 bg-black/10 rounded-full blur-2xl" />
                <div className="relative z-10">
                  <h3 className="text-2xl md:text-3xl font-bold mb-4">Bạn đã sẵn sàng có một CV chuẩn ATS?</h3>
                  <p className="text-white/90 text-lg mb-8 max-w-2xl mx-auto">
                    Tạo CV chuyên nghiệp, chuẩn ATS và chinh phục nhà tuyển dụng ngay hôm nay với công cụ của Đậu.
                  </p>
                  <Link href="/cv-builder" className="inline-flex items-center justify-center bg-white text-[#2E7D32] px-8 py-3.5 rounded-full font-bold text-lg hover:bg-gray-50 transition-colors shadow-sm">
                    Tạo CV Miễn Phí Ngay
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </div>
              </div> */}
            </main>

            {/* Sidebar (Right) */}
            <aside className="w-full lg:w-[360px] flex flex-col gap-8">
              {/* Sticky Table of Contents */}
              <BlogTOC headings={headings} />

              {/* Related Blogs */}
              {relatedPosts.length > 0 && (
                <div className="bg-white p-6 rounded-3xl shadow-sm border border-[#2F4F4F]/5">
                  <h3 className="text-lg font-bold text-[#2F4F4F] mb-6 flex items-center gap-2">
                    <BookOpen className="w-5 h-5 text-[var(--primary)]" />
                    Bài viết liên quan
                  </h3>
                  <div className="flex flex-col gap-5">
                    {relatedPosts.map(rp => (
                      <Link href={`/blog/${rp.slug}`} key={rp.slug} className="group flex gap-4 items-start">
                        <div className="w-20 h-20 rounded-xl overflow-hidden flex-shrink-0">
                          <img src={rp.coverImage} alt={rp.title} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-[#2F4F4F] group-hover:text-[var(--primary)] transition-colors line-clamp-2 mb-1">
                            {rp.title}
                          </h4>
                          <p className="text-xs text-gray-500">{rp.date}</p>
                          {rp.sharedTags && rp.sharedTags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {rp.sharedTags.slice(0, 2).map(tag => (
                                <span key={tag} className="text-[10px] bg-[#E8F5E9] text-[#2E7D32] px-1.5 py-0.5 rounded-full">{tag}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Sidebar CTA */}
              <div className="bg-[#F9F9F2] p-8 rounded-3xl shadow-sm border border-[#2E7D32]/20 text-center">
                <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm">
                  <Sparkles className="w-8 h-8 text-[var(--primary)]" />
                </div>
                <h4 className="text-xl font-bold text-[#2F4F4F] mb-3">Tối ưu CV bằng AI</h4>
                <p className="text-sm text-gray-600 mb-6">
                  Nhận đánh giá chi tiết và gợi ý cải thiện CV để tăng 80% cơ hội trúng tuyển.
                </p>
                <Link href="/cv-analyzer" className="block w-full bg-[var(--primary)] text-white px-4 py-3 rounded-xl font-bold text-sm hover:bg-[#2E7D32] transition-colors">
                  Khám phá ngay
                </Link>
              </div>
            </aside>
          </div>
        </div>
        <Footer />
      </div>
    );
  } catch (error) {
    notFound();
  }
}
