import type { CVAnalysisResponse } from "@/types";
import { TrendingUp, CheckCircle, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function MatchDashboard({ result }: { result: CVAnalysisResponse }) {
  return (
    <div>
      {/* Title */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-6"
      >
        <h1 style={{ fontSize: 'clamp(2rem, 4vw, 3rem)', fontWeight: 700, color: '#2F4F4F' }} className="mb-1">
          Kết quả phân tích
        </h1>
        <p className="text-lg text-[#2F4F4F]/70">
          Dựa trên JD và nội dung CV của bạn
        </p>
      </motion.div>

      {/* Match Score Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <div className="bg-gradient-to-br from-[var(--primary)] to-[var(--primary)]/80 rounded-3xl p-12 text-center relative overflow-hidden shadow-xl">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/10 rounded-full blur-3xl" />

          <div className="relative z-10">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
              className="mb-1"
            >
              <div className="inline-block p-8 bg-white/20 backdrop-blur-sm rounded-full">
                <TrendingUp className="w-16 h-16 text-white" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div style={{ fontSize: '4rem', fontWeight: 700 }} className="text-white mb-2">
                {result.match_score}%
              </div>
              <h2 className="text-2xl font-semibold text-white/90 mb-3">
                Độ phù hợp với JD
              </h2>
              <p className="text-white/80 text-lg max-w-2xl mx-auto">
                {result.match_score >= 80 
                  ? "Tuyệt vời! CV của bạn có khả năng cao lọt vào vòng phỏng vấn." 
                  : "CV của bạn khá ổn! Hãy điều chỉnh thêm từ khóa để cải thiện độ khớp nhé."}
              </p>
            </motion.div>
          </div>
        </div>
      </motion.div>

      {/* Metrics Grid */}
      <div className="grid lg:grid-cols-2 gap-8 mb-8">
        {/* Good Metrics */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="flex flex-col items-left justify-between bg-white rounded-3xl p-8 border-2 border-[var(--primary)]/10 h-full">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-[var(--primary)]/10 rounded-xl flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-[var(--primary)]" />
              </div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Điểm sáng của CV</h2>
            </div>

            <div className="flex flex-wrap gap-3">
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
                className="px-4 py-2 bg-[var(--primary)]/10 text-[#2F4F4F] rounded-xl border-2 border-[var(--primary)]/20 font-medium"
              >
                Tác động: {result.impact_score}/10
              </motion.div>
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.35 }}
                className="px-4 py-2 bg-[var(--primary)]/10 text-[#2F4F4F] rounded-xl border-2 border-[var(--primary)]/20 font-medium"
              >
                Giọng văn: {result.tone}
              </motion.div>
            </div>

            <div className="mt-6 p-4 bg-[var(--primary)]/5 rounded-2xl">
              <p className="text-sm text-[#2F4F4F]/70">
                <strong>✅ Rất tốt!</strong> Tone giọng và điểm tác động của cấu trúc nội dung hiện tại đạt chuẩn chuyên nghiệp.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Missing Keywords */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="bg-white rounded-3xl p-8 border-2 border-[#B22222]/10 h-full">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-[#B22222]/10 rounded-xl flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-[#B22222]" />
              </div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Từ khóa cần bổ sung</h2>
            </div>

            <div className="flex flex-wrap gap-3">
              {result.missing_keywords.length > 0 ? result.missing_keywords.map((kw, index) => (
                <motion.div
                  key={kw}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.4 + index * 0.05 }}
                  className="px-4 py-2 bg-[#B22222]/10 text-[#B22222] rounded-xl border-2 border-[#B22222]/20 font-medium"
                >
                  {kw}
                </motion.div>
              )) : (
                 <div className="text-sm text-[#5A6D6D]">Không phát hiện từ khóa quan trọng nào bị thiếu.</div>
              )}
            </div>

            {result.missing_keywords.length > 0 && (
              <div className="mt-6 p-4 bg-[#B22222]/5 rounded-2xl">
                <p className="text-sm text-[#2F4F4F]/70">
                  <strong>⚠️ Lưu ý:</strong> JD yêu cầu những kỹ năng này nhưng chưa thấy trong CV của bạn.
                </p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
