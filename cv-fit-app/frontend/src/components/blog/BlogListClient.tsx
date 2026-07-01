'use client';

import { useState, useMemo, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { OmitBlogPost } from '@/lib/mdx';
import BlogCard from './BlogCard';

interface BlogListClientProps {
  posts: OmitBlogPost[];
}

const POSTS_PER_PAGE = 9;

function getAllCategories(posts: OmitBlogPost[]): string[] {
  const cats = new Set<string>();
  posts.forEach((p) => {
    if (p.category) cats.add(p.category);
  });
  return ['Tất cả', ...Array.from(cats)];
}

export default function BlogListClient({ posts }: BlogListClientProps) {
  const allCategories = useMemo(() => getAllCategories(posts), [posts]);

  const [activeCategory, setActiveCategory] = useState('Tất cả');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Sync search from the DOM input in the hero section
  useEffect(() => {
    const input = document.getElementById('blog-search') as HTMLInputElement | null;
    if (!input) return;

    const syncFromDom = () => {
      setSearchQuery(input.value);
    };

    // Initial sync
    syncFromDom();

    input.addEventListener('input', syncFromDom);
    return () => {
      input.removeEventListener('input', syncFromDom);
    };
  }, []);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [activeCategory, searchQuery]);

  const filteredPosts = useMemo(() => {
    let result = posts;

    if (activeCategory !== 'Tất cả') {
      result = result.filter((p) => p.category === activeCategory);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      result = result.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q)
      );
    }

    return result;
  }, [posts, activeCategory, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredPosts.length / POSTS_PER_PAGE));

  const paginatedPosts = useMemo(() => {
    const start = (currentPage - 1) * POSTS_PER_PAGE;
    return filteredPosts.slice(start, start + POSTS_PER_PAGE);
  }, [filteredPosts, currentPage]);

  return (
    <>
      {/* Category Filters */}
      <div className="flex items-center gap-6 flex-wrap w-full no-scrollbar pb-2 my-4">
        {allCategories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={
              activeCategory === cat
                ? 'bg-green-50 text-[var(--primary)] px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap'
                : 'text-gray-500 hover:text-[#2F4F4F] font-medium text-sm whitespace-nowrap cursor-pointer px-2 py-2 transition-colors'
            }
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Blog Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
        {paginatedPosts.map((post) => (
          <BlogCard key={post.slug} post={post} />
        ))}
      </div>

      {/* No results */}
      {filteredPosts.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg">
            Không tìm thấy bài viết nào.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-16 mb-8">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-[#2F4F4F] px-3 py-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} />
            Trước
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
            <button
              key={page}
              onClick={() => setCurrentPage(page)}
              className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-bold transition-colors ${
                currentPage === page
                  ? 'bg-green-50 text-[var(--primary)]'
                  : 'hover:bg-gray-100 text-gray-600 font-medium'
              }`}
            >
              {page}
            </button>
          ))}

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-[#2F4F4F] px-3 py-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Tiếp
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </>
  );
}
