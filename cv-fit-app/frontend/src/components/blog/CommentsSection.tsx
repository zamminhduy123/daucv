"use client";

import React from 'react';
import { MessageSquare, Heart, CornerDownRight } from 'lucide-react';

export interface Comment {
  id: string;
  author: string;
  avatar: string;
  text: string;
  timestamp: string;
  likes: number;
}

const mockComments: Comment[] = [
  {
    id: "1",
    author: "Nguyễn Văn A",
    avatar: "https://ui-avatars.com/api/?name=Nguyễn+Văn+A&background=random",
    text: "Bài viết rất hữu ích, cảm ơn Đậu! Cho mình hỏi ATS có đọc được file PDF export từ Canva không?",
    timestamp: "2 giờ trước",
    likes: 12
  },
  {
    id: "2",
    author: "Trần Thị B",
    avatar: "https://ui-avatars.com/api/?name=Trần+Thị+B&background=random",
    text: "Mình đã thử áp dụng cách này và thấy CV gọn gàng hơn hẳn. Hy vọng sẽ sớm nhận được phản hồi từ HR.",
    timestamp: "5 giờ trước",
    likes: 5
  }
];

export function CommentsSection() {
  return (
    <div className="mt-16 bg-white p-8 md:p-12 rounded-3xl shadow-sm border border-[#2F4F4F]/5">
      <h3 className="text-2xl font-bold text-[#2F4F4F] mb-8 font-heading flex items-center gap-3 border-none pb-0 m-0">
        <MessageSquare className="w-6 h-6 text-[var(--primary)]" />
        Bình luận ({mockComments.length})
      </h3>
      
      {/* Input Area */}
      <div className="flex gap-4 mb-10 mt-8">
        <img 
          src="https://ui-avatars.com/api/?name=Guest&background=E8F5E9&color=2E7D32" 
          alt="Avatar" 
          className="w-10 h-10 rounded-full flex-shrink-0"
        />
        <div className="flex-1 flex flex-col gap-3">
          <textarea 
            placeholder="Bạn nghĩ gì về bài viết này? Viết bình luận..." 
            className="w-full bg-[#F9F9F2] border border-gray-200 rounded-2xl p-4 min-h-[100px] outline-none focus:border-[#2E7D32] focus:ring-1 focus:ring-[#2E7D32] transition-all resize-none text-gray-700 text-sm font-medium"
          />
          <div className="flex justify-end">
            <button className="bg-[var(--primary)] text-white px-6 py-2.5 rounded-full font-semibold hover:bg-[#2E7D32] transition-colors text-sm">
              Gửi bình luận
            </button>
          </div>
        </div>
      </div>

      {/* Comments List */}
      <div className="flex flex-col gap-6">
        {mockComments.map((comment) => (
          <div key={comment.id} className="flex gap-4">
            <img src={comment.avatar} alt={comment.author} className="w-10 h-10 rounded-full flex-shrink-0" />
            <div className="flex-1">
              <div className="bg-[#F9F9F2] p-4 rounded-2xl rounded-tl-none inline-block max-w-full">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-[#2F4F4F] text-sm">{comment.author}</span>
                  <span className="text-xs text-gray-500">{comment.timestamp}</span>
                </div>
                <p className="text-gray-700 text-sm leading-relaxed m-0">{comment.text}</p>
              </div>
              <div className="flex items-center gap-4 mt-2 ml-2">
                <button className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-red-500 transition-colors font-medium">
                  <Heart className="w-3.5 h-3.5" />
                  {comment.likes > 0 ? comment.likes : 'Thích'}
                </button>
                <button className="flex items-center gap-1 text-xs text-gray-500 hover:text-[var(--primary)] transition-colors font-medium">
                  <CornerDownRight className="w-3.5 h-3.5" />
                  Phản hồi
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
