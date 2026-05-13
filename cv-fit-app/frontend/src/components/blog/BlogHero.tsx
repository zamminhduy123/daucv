import React from 'react';
import { BlogMeta, BlogMetaProps } from './BlogMeta';

export interface BlogHeroProps extends BlogMetaProps {
  category: string;
  title: string;
  description?: string;
  coverImage?: string;
}

export function BlogHero({ category, title, description, coverImage, ...metaProps }: BlogHeroProps) {
  return (
    <div className="mb-12">
      <div className="mb-4">
        <span className="inline-block bg-[#E8F5E9] text-[#2E7D32] px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase">
          {category}
        </span>
      </div>

      <h1 className="text-3xl md:text-5xl font-extrabold text-[#2F4F4F] font-heading mb-6 leading-tight">
        {title}
      </h1>
      
      <BlogMeta {...metaProps} />

      {description && (
        <p className="text-xl text-gray-600 leading-relaxed mb-8 font-medium">
          {description}
        </p>
      )}

      {coverImage && (
        <div className="relative w-full aspect-video rounded-3xl overflow-hidden shadow-sm">
          <img src={coverImage} alt={title} className="w-full h-full object-cover" />
        </div>
      )}
    </div>
  );
}
