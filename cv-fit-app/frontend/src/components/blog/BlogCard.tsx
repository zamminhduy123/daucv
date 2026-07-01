'use client';

import Link from 'next/link';
import { Clock } from 'lucide-react';

interface BlogCardProps {
  post: {
    slug: string;
    title: string;
    description: string;
    category: string;
    readTime: string;
    author: string;
    authorAvatar: string;
    coverImage: string;
    date: string;
    tags?: string[];
  };
  tag?: string;
}

export default function BlogCard({ post, tag }: BlogCardProps) {
  return (
    <Link href={`/blog/${post.slug}`} className="group block h-full">
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

          {/* Tags */}
          {post.tags && post.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {post.tags.slice(0, 3).map((t) => (
                <Link
                  key={t}
                  href={`/blog/tag/${encodeURIComponent(t)}`}
                  onClick={(e) => e.stopPropagation()}
                  className={`text-[10px] px-2 py-0.5 rounded-full transition-colors ${
                    tag === t
                      ? 'bg-[var(--primary)] text-white'
                      : 'bg-[#E8F5E9] text-[#2E7D32]'
                  }`}
                >
                  {t}
                </Link>
              ))}
            </div>
          )}

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
  );
}
