import React from 'react';

export function BlogContentLayout({ children }: { children: React.ReactNode }) {
  return (
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
      {children}
    </article>
  );
}
