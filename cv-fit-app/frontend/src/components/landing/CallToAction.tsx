'use client';

import Link from "next/link";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

export default function CallToAction() {
  return (
    <motion.section
      className="mx-auto text-center px-4 sm:px-6 lg:px-12 py-20 lg:py-32 bg-white"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
    >
      <motion.h2
        className="font-heading font-bold leading-tight text-[#2F4F4F] mb-6 md:mb-10"
        style={{ fontSize: "clamp(2.5rem,6vw,5rem)" }}
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        whileInView={{ opacity: 1, y: 0, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        Sẵn sàng để ĐẬU?
      </motion.h2>
      <motion.p
        className="text-[#5A6D6D] leading-relaxed max-w-[800px] mx-auto mb-10 md:mb-14 text-base md:text-xl px-4"
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        Đừng để một bản CV cũ kỹ cản bước bạn. Hãy để Đậu giúp bạn tỏa sáng ngay hôm nay.
      </motion.p>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.3 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.97 }}
      >
        <Link href="/app/setup" className="btn-green btn-green--lg">
          Bắt đầu ngay <ChevronRight size={24} />
        </Link>
      </motion.div>
    </motion.section>
  );
}
