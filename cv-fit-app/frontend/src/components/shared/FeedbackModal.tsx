"use client";

import React, { useState } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useAuth } from "@/context/AuthContext";
import { submitFeedbackAPI } from "@/lib/api";
import { X, Star, Send, Gem, CheckCircle, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

export default function FeedbackModal() {
  const { isFeedbackOpen, setFeedbackOpen } = useWorkspace();
  const { status, refreshCredits } = useAuth();
  
  const [rating, setRating] = useState<number>(5);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [successData, setSuccessData] = useState<{
    message: string;
    credits_rewarded: number;
    new_credits: number;
  } | null>(null);

  if (!isFeedbackOpen) return null;

  const handleClose = () => {
    setFeedbackOpen(false);
    // Reset form after transition
    setTimeout(() => {
      setRating(5);
      setContent("");
      setSuccessData(null);
      setLoading(false);
    }, 300);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (status !== "authenticated") {
      toast.error("Vui lòng đăng nhập để gửi ý kiến phản hồi và nhận credit!");
      return;
    }

    if (content.trim().length < 5) {
      toast.error("Nội dung đánh giá phải có ít nhất 5 ký tự.");
      return;
    }

    setLoading(true);
    try {
      const data = await submitFeedbackAPI(rating, content);
      if (data.success) {
        setSuccessData({
          message: data.message,
          credits_rewarded: data.credits_rewarded,
          new_credits: data.new_credits,
        });
        toast.success("Cảm ơn bạn đã gửi đánh giá phản hồi!");
        // Refresh credits balance in sidebar
        refreshCredits();
      } else {
        toast.error(data.message || "Không thể gửi ý kiến phản hồi.");
      }
    } catch (err: unknown) {
      console.error(err);
      const msg = err instanceof Error ? err.message : "Đã xảy ra lỗi khi gửi phản hồi.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleClose}
          className="absolute inset-0 bg-[#2F4F4F]/40 backdrop-blur-xs"
        />

        {/* Modal content */}
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 15 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 15 }}
          transition={{ type: "spring", duration: 0.4 }}
          className="relative bg-[#FEFDF8] w-full max-w-md rounded-3xl p-6 shadow-xl border border-gray-100/50 overflow-hidden z-10"
        >
          {/* Close button */}
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 p-1.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={18} />
          </button>

          {!successData ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-5 mt-2">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 bg-[var(--primary)]/10 rounded-xl flex items-center justify-center text-[var(--primary)]">
                  <MessageSquare size={20} />
                </div>
                <div>
                  <h3 className="font-heading font-extrabold text-[#2F4F4F] text-lg leading-tight">
                    Đóng góp ý kiến & phản hồi
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Giúp ĐẬU thông minh hơn & nhận ngay credit miễn phí!
                  </p>
                </div>
              </div>

              <div className="h-[1px] bg-gray-100" />

              {/* Star Rating */}
              <div className="flex flex-col items-center gap-2 py-1">
                <span className="text-xs font-semibold text-[#2F4F4F]/80">
                  Mức độ hài lòng của bạn
                </span>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((star) => {
                    const active = star <= (hoverRating ?? rating);
                    return (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setRating(star)}
                        onMouseEnter={() => setHoverRating(star)}
                        onMouseLeave={() => setHoverRating(null)}
                        className="p-1 transition-transform active:scale-90"
                      >
                        <Star
                          size={32}
                          className={`transition-colors duration-200 ${
                            active
                              ? "fill-amber-400 text-amber-400"
                              : "text-gray-300"
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Textarea */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-[#2F4F4F]/80">
                  Nhận xét hoặc đề xuất tính năng mới
                </label>
                <textarea
                  required
                  rows={4}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Ứng dụng rất hữu ích! Tôi đề xuất thêm tính năng..."
                  className="w-full text-sm border border-gray-200 rounded-2xl p-3 bg-white focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30 focus:border-[var(--primary)] transition-all resize-none text-[#2F4F4F]"
                />
              </div>

              {/* Warning/Gift Alert */}
              <div className="bg-[#FEF9E6] border border-[#FBE6A9] p-3 rounded-2xl flex gap-2.5">
                <Gem size={16} className="text-amber-600 shrink-0 mt-0.5" />
                <p className="text-[11px] text-[#8A6700] leading-relaxed font-medium">
                  Với lượt gửi phản hồi đầu tiên, bạn sẽ nhận được ngay{" "}
                  <span className="font-bold">+5 credits</span> cộng vào số dư tài khoản.
                </p>
              </div>

              {/* Actions */}
              <div className="flex flex-col sm:flex-row gap-2 mt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 btn-green flex items-center justify-center gap-2 py-3 rounded-2xl text-white font-bold text-sm"
                >
                  {loading ? (
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      Gửi đánh giá <Send size={14} />
                    </>
                  )}
                </button>
                <a
                  href="https://t.me/Rozzy148"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 border border-gray-200 hover:bg-gray-50 flex items-center justify-center gap-2 py-3 rounded-2xl text-[#2F4F4F] font-bold text-sm no-underline transition-colors"
                >
                  Hợp tác dự án khác 🤝
                </a>
              </div>
            </form>
          ) : (
            <div className="flex flex-col items-center text-center gap-5 py-4 mt-2">
              <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-500 shadow-xs">
                <CheckCircle size={36} />
              </div>
              <div>
                <h3 className="font-heading font-extrabold text-[#2F4F4F] text-lg leading-tight">
                  Gửi đánh giá thành công!
                </h3>
                <p className="text-xs text-gray-500 mt-1 max-w-[280px] mx-auto leading-relaxed">
                  Cảm ơn bạn đã đóng góp phản hồi để đồng hành và phát triển cùng ĐẬU.
                </p>
              </div>

              {successData.credits_rewarded > 0 ? (
                <div className="bg-emerald-50 border border-emerald-100 rounded-2xl px-4 py-3 flex items-center gap-3">
                  <Gem size={20} className="text-emerald-600 animate-bounce" />
                  <div className="text-left">
                    <span className="text-[11px] font-bold text-emerald-700 block uppercase tracking-wide">
                      Phần thưởng phản hồi
                    </span>
                    <span className="text-sm font-extrabold text-emerald-800">
                      +{successData.credits_rewarded} credits đã được cộng!
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-gray-400 font-medium">
                  (Ý kiến đóng góp của bạn đã được ghi nhận trong hệ thống)
                </p>
              )}

              <div className="h-[1px] bg-gray-100 w-full" />

              <div className="flex flex-col gap-2 w-full">
                <a
                  href="https://t.me/Rozzy148"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-green flex items-center justify-center gap-2 py-3 rounded-2xl text-white font-bold text-sm no-underline"
                >
                  Liên hệ hợp tác dự án khác 🤝
                </a>
                <button
                  onClick={handleClose}
                  className="w-full border border-gray-200 hover:bg-gray-50 py-3 rounded-2xl text-gray-500 font-bold text-sm transition-colors"
                >
                  Đóng
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
