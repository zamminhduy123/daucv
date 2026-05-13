import React from 'react';
import { Calendar, Clock, Share2, Mail, Link as LinkIcon } from 'lucide-react';

export interface BlogMetaProps {
  author: string;
  authorAvatar?: string;
  date: string;
  readTime: string;
  showShareIcons?: boolean;
}

export function BlogMeta({ author, authorAvatar, date, readTime, showShareIcons = true }: BlogMetaProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#2F4F4F]/10 pb-6 mb-8">
      <div className="flex items-center gap-6 text-sm text-[#5A6D6D]">
        <div className="flex items-center gap-2">
          {authorAvatar && (
            <img src={authorAvatar} alt={author} className="w-8 h-8 rounded-full bg-gray-200" />
          )}
          <span className="font-medium text-[#2F4F4F]">{author}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Calendar className="w-4 h-4 text-[var(--primary)]" />
          <time dateTime={date}>{date}</time>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-[var(--primary)]" />
          <span>{readTime}</span>
        </div>
      </div>
      
      {showShareIcons && (
        <div className="flex items-center gap-3">
          <button className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500 hover:text-[var(--primary)] hover:border-[var(--primary)] transition-colors shadow-sm" aria-label="Share">
            <Share2 className="w-4 h-4" />
          </button>
          <button className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500 hover:text-[var(--primary)] hover:border-[var(--primary)] transition-colors shadow-sm" aria-label="Share via Email">
            <Mail className="w-4 h-4" />
          </button>
          <button className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500 hover:text-[var(--primary)] hover:border-[var(--primary)] transition-colors shadow-sm" aria-label="Copy Link">
            <LinkIcon className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
