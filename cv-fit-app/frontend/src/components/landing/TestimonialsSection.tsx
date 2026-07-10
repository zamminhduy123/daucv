"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { MessageSquare, ArrowRight, Quote, Sparkles, Star } from "lucide-react";

interface FeedbackItem {
  id: string;
  name: string | null;
  avatar: string | null;
  rating: number;
  content: string;
  created_at: string;
}

export default function TestimonialsSection() {
  const { status } = useSession();
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);

  const feedbackUrl = status === "authenticated"
    ? "/app/setup?feedback=true"
    : "/login?callbackUrl=/app/setup?feedback=true";

  useEffect(() => {
    fetch("/api/feedbacks")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch testimonials");
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setFeedbacks(data);
        }
      })
      .catch((err) => console.error("Error loading testimonials:", err))
      .finally(() => setLoading(false));
  }, []);

  const hasFeedbacks = feedbacks.length > 0;

  return (
    <section className="py-20 lg:py-28 bg-[#FEFDF8]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Decorative badge */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#85AE7B]/20 text-[#2F4F4F] text-xs font-bold tracking-wide uppercase mb-4"
        >
          <Sparkles size={12} className="text-[#85AE7B]" /> Cảm nhận khách hàng
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="font-heading font-extrabold text-[#2F4F4F] text-3xl md:text-4xl tracking-tight mb-4"
        >
          Đồng hành cùng hàng ngàn ứng viên
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.15 }}
          className="text-[#5A6D6D] max-w-xl mx-auto text-sm md:text-base leading-relaxed mb-12"
        >
          Những chia sẻ chân thực từ những người đã tối ưu CV và bứt phá sự nghiệp thành công cùng ĐẬU.
        </motion.p>

        {loading ? (
          <div className="flex justify-center py-10">
            <div className="w-8 h-8 border-4 border-[#85AE7B] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : hasFeedbacks ? (
          <div className="flex flex-col gap-12 items-center">
            {/* Feedbacks Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full text-left">
              {feedbacks.map((item, idx) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.1, type: "spring", stiffness: 100 }}
                  className="bg-white border border-gray-100 rounded-3xl p-6 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow relative overflow-hidden"
                >
                  <Quote className="absolute right-4 top-4 text-gray-50/70 w-12 h-12 pointer-events-none stroke-[1]" />
                  
                  <div>
                    {/* Stars */}
                    <div className="flex gap-0.5 mb-4">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star
                          key={i}
                          size={14}
                          className={
                            i < item.rating
                              ? "fill-amber-400 text-amber-400"
                              : "text-gray-200"
                          }
                        />
                      ))}
                    </div>

                    {/* Review text */}
                    <p className="text-sm text-[#2F4F4F] leading-relaxed italic mb-6">
                      &quot;{item.content}&quot;
                    </p>
                  </div>

                  {/* Profile block */}
                  <div className="flex items-center gap-3 border-t border-gray-50 pt-4 mt-auto">
                    {item.avatar ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={item.avatar}
                        alt={item.name || "Avatar"}
                        className="w-10 h-10 rounded-full border border-gray-100 shadow-2xs"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-[#85AE7B]/20 text-[#2F4F4F] font-bold text-sm rounded-full flex items-center justify-center">
                        {item.name?.[0]?.toUpperCase() || "U"}
                      </div>
                    )}
                    <div>
                      <span className="text-sm font-bold text-[#2F4F4F] block">
                        {item.name || "Người dùng ẩn danh"}
                      </span>
                      <span className="text-[10px] text-gray-400 font-medium">
                        {new Date(item.created_at).toLocaleDateString("vi-VN")}
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Testimonial Section Bottom CTAs */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
              <Link
                href={feedbackUrl}
                className="btn-green flex items-center gap-2 px-6 py-3 rounded-2xl text-white text-sm font-bold no-underline hover:opacity-95 transition-all shadow-sm"
              >
                Viết thêm nhận xét <MessageSquare size={16} />
              </Link>
              <a
                href="https://t.me/Rozzy148"
                target="_blank"
                rel="noopener noreferrer"
                className="border border-gray-200 hover:bg-gray-50 flex items-center gap-2 px-6 py-3 rounded-2xl text-[#2F4F4F] text-sm font-bold no-underline transition-colors"
              >
                Hợp tác dự án khác <ArrowRight size={16} />
              </a>
            </div>
          </div>
        ) : (
          /* Empty state container */
          <motion.div
            initial={{ opacity: 0, y: 25 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, type: "spring", stiffness: 100 }}
            className="relative bg-white border border-gray-100 rounded-[2rem] p-8 md:p-12 shadow-sm max-w-2xl mx-auto overflow-hidden"
          >
            {/* Subtle background decoration */}
            <div className="absolute -top-10 -right-10 w-40 h-40 bg-[#85AE7B]/5 rounded-full blur-2xl pointer-events-none" />
            <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-amber-500/5 rounded-full blur-2xl pointer-events-none" />

            {/* Large Quote icon */}
            <Quote className="text-gray-100 w-20 h-20 mx-auto mb-4 stroke-[1.5]" />

            <p className="text-base md:text-lg text-[#2F4F4F]/90 font-medium italic leading-relaxed mb-6">
              &quot;Chưa có đánh giá nào được công khai. Hãy là người đầu tiên trải nghiệm tính năng chuẩn hóa CV, phỏng vấn thử cùng AI và chia sẻ nhận xét của bạn để nhận ngay phần thưởng credit!&quot;
            </p>

            <div className="h-[1px] bg-gray-100 my-6 max-w-xs mx-auto" />

            <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
              <Link
                href={feedbackUrl}
                className="btn-green flex items-center gap-2 px-6 py-3 rounded-2xl text-white text-sm font-bold no-underline hover:opacity-95 transition-all shadow-sm w-full sm:w-auto justify-center"
              >
                Viết đánh giá phản hồi <MessageSquare size={16} />
              </Link>
              <a
                href="https://t.me/Rozzy148"
                target="_blank"
                rel="noopener noreferrer"
                className="border border-gray-200 hover:bg-gray-50 flex items-center gap-2 px-6 py-3 rounded-2xl text-[#2F4F4F] text-sm font-bold no-underline transition-colors w-full sm:w-auto justify-center"
              >
                Hợp tác dự án khác <ArrowRight size={16} />
              </a>
            </div>
          </motion.div>
        )}
      </div>
    </section>
  );
}
