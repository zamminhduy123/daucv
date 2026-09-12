'use client';

import { motion } from "motion/react";
import Link from "next/link";
import { ArrowRight, Play } from "lucide-react";

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.2,
    },
  },
};

export default function HeroSection() {
  return (
    <section
      className="relative overflow-hidden pt-4"
    >
      <div
        className="pointer-events-none absolute right-[3%] top-1/2 hidden w-[46%] -translate-y-1/2 lg:block"
        aria-hidden="true"
      >
        <video
          className="w-full object-cover object-center"
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster="/bg2.webp"
          disablePictureInPicture
        >
          <source src="/hero.webm" type="video/webm" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-r from-[#FEFDF8] via-transparent to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-l from-[#FEFDF8] via-transparent to-transparent" />
      </div>
      <motion.div
        className="max-w-7xl mx-auto px-6 relative z-10 flex flex-col items-center lg:items-start"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Content */}
        <div className="z-10 text-center lg:text-left lg:max-w-2xl">
          {/* Badge */}
          <motion.div
            className="inline-flex items-center justify-center gap-2 text-center rounded-full mb-6 lg:mb-8 max-w-full text-[13px] font-bold text-[#2D7A58]"
            style={{ padding: "0.5rem 1rem", backgroundColor: "#EAF5EC" }}
            initial={{ opacity: 0, y: 12, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <span className="text-(--primary) text-base shrink-0">🌱</span>
            <span className="leading-tight sm:leading-normal">Công cụ AI giúp bạn tối ưu CV và luyện phỏng vấn</span>
          </motion.div>

          {/* H1 */}
          <motion.h1
            className="font-heading font-bold leading-tight text-[#2F4F4F] mb-4 lg:mb-6"
            style={{ letterSpacing: "-0.03em", fontSize: "clamp(2.5rem, 5.5vw, 4.2rem)" }}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            Sửa CV chuẩn ATS.<br />
            <span className="text-(--primary)">Luyện phỏng vấn AI theo JD.</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            className="text-[#3F5454] leading-relaxed mb-8 mx-auto lg:mx-0 text-base lg:text-xl"
            style={{ maxWidth: "600px" }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.55 }}
          >
            Tải CV và Job Description để Đậu phân tích độ phù hợp, gợi ý sửa CV chuẩn ATS, tìm kỹ năng còn thiếu và luyện phỏng vấn 1-1 bằng AI.
          </motion.p>

          {/* CTA */}
          <motion.div
            className="flex flex-col sm:flex-row gap-4 items-center justify-center lg:justify-start mb-6"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.7 }}
          >
            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} className="w-full sm:w-auto">
              <Link href="/app/setup" className="group px-6 py-4 lg:px-8 bg-(--primary) text-white rounded-xl font-bold hover:opacity-90 transition-all shadow-md flex w-full sm:w-auto justify-center items-center gap-2 text-base lg:text-lg">
                Phân tích CV/JD <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
              </Link>
            </motion.div>
            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} className="w-full sm:w-auto">
              <Link
                href="/app"
                className="flex w-full sm:w-auto items-center justify-center gap-3 px-6 py-4 lg:px-8 rounded-xl font-bold bg-white text-[#2F4F4F] border border-gray-200 hover:shadow-md transition-all text-base lg:text-lg"
              >
                <div className="bg-[#2D7A58] rounded-full p-2 text-white flex items-center justify-center"><Play size={16} fill="currentColor" /></div>
                Phỏng vấn thử
              </Link>
            </motion.div>
          </motion.div>

        </div>

      </motion.div>
    </section>
  );
}
