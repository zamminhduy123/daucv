'use client';

import { motion } from 'framer-motion';
import Image from "next/image";
import type { HowItWorksStep } from "@/types";

interface StepData extends HowItWorksStep {
  img: string;
}

const STEPS: StepData[] = [
  {
    n: "1",
    t: "Tải CV & JD",
    d: "Tải lên CV của bạn và mô tả công việc (JD).",
    img: "/upload.webp",
  },
  {
    n: "2",
    t: "AI phân tích",
    d: "Đậu sẽ phân tích, chấm điểm và gợi ý cách cải thiện.",
    img: "/analyze.webp",
  },
  {
    n: "3",
    t: "Luyện tập & tự tin",
    d: "Luyện phỏng vấn 1-1 và nhận góp ý chi tiết để tự tin chinh phục nhà tuyển dụng.",
    img: "/trophy.webp",
  },
];

export default function HowItWorksSection() {
  return (
    <section id="cách-hoạt-động" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-20">
      <div className="text-center mb-16">
        <motion.h2
          className="font-heading font-bold text-[#2F4F4F] text-3xl md:text-4xl mb-4"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Bắt đầu với Đậu chỉ trong 3 bước
        </motion.h2>
      </div>

      <motion.div
        className="flex flex-col lg:flex-row items-stretch justify-between gap-8 relative"
        initial="hidden"
        whileInView="visible"
        viewport={{ amount: 0.1, once: true }}
        variants={{
          hidden: {},
          visible: {
            transition: { staggerChildren: 0.15 },
          },
        }}
      >
        {STEPS.map((s) => (
          <div key={s.n} className="flex flex-1 items-stretch w-full lg:w-auto">
            <motion.div
              variants={{
                hidden: { opacity: 0, y: 30 },
                visible: {
                  opacity: 1,
                  y: 0,
                  transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] },
                },
              }}
              whileHover={{ y: -4 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              <div className="bg-white rounded-3xl pt-8 pb-16 px-8 border border-gray-100 shadow-sm relative flex-1 min-h-55 overflow-hidden group">
                {/* Image as background element with offset */}
                <div className="absolute -bottom-4 -right-4 w-40 h-40 opacity-20 lg:opacity-100 lg:w-44 lg:h-44 transition-transform group-hover:scale-110 duration-500">
                  <Image
                    src={s.img}
                    alt={s.t}
                    fill
                    className="object-contain"
                  />
                </div>

                <div className="relative z-10">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-10 h-10 rounded-full bg-(--primary) text-white flex items-center justify-center font-bold text-lg shadow-sm">
                      {s.n}
                    </div>
                    <h3 className="font-heading font-bold text-[#2F4F4F] text-xl">
                      {s.t}
                    </h3>
                  </div>
                  <p className="text-[#5A6D6D] text-sm leading-relaxed max-w-60 mr-18">
                    {s.d}
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        ))}
      </motion.div>
    </section>
  );
}
