import { Sparkles, HelpCircle } from "lucide-react";
import type { SuggestedEdit } from "@/types";
import { motion } from "framer-motion";

export default function DiffViewer({ edits }: { edits: SuggestedEdit[] }) {
  if (!edits || edits.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="mt-8 mb-8"
    >
      <div className="bg-white rounded-3xl p-8 border-2 border-[#98C18E]/10 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-[#98C18E]/10 rounded-xl flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-[#98C18E]" />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#2F4F4F' }}>Gợi ý cải thiện</h2>
        </div>

        <div className="space-y-6">
          {edits.map((entry, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className="flex gap-4 p-6 bg-[#F9F9F2] rounded-2xl border border-[#98C18E]/10"
            >
              {/* Number Badge */}
              <div className="flex-shrink-0 w-8 h-8 bg-[#98C18E] text-white rounded-full flex items-center justify-center font-bold">
                {index + 1}
              </div>

              {/* Edit content */}
              <div className="flex-1 space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  {/* Original */}
                  <div className="p-4 bg-white/50 rounded-xl border border-[#B22222]/10 relative">
                    <div className="text-[10px] uppercase font-bold text-[#B22222]/70 tracking-widest mb-2">Bản gốc</div>
                    <p className="text-sm leading-relaxed line-through opacity-70 text-[#991B1B]">
                      {entry.original_text}
                    </p>
                  </div>
                  {/* Upgraded */}
                  <div className="p-4 bg-white rounded-xl border border-[#98C18E]/20 shadow-sm relative">
                    <div className="text-[10px] uppercase font-bold text-[#98C18E] tracking-widest mb-2">Bản nâng cấp</div>
                    <p
                      className="text-sm leading-relaxed text-[#2F4F4F] font-medium"
                      dangerouslySetInnerHTML={{ __html: entry.upgraded_text }}
                    />
                  </div>
                </div>

                {/* Reason */}
                <div className="flex items-start gap-2 bg-white/60 p-3 rounded-xl border border-[#2F4F4F]/[0.05]">
                  <HelpCircle size={16} className="shrink-0 mt-0.5 text-[#5A6D6D]" />
                  <p className="text-sm text-[#2F4F4F]/80 leading-relaxed">{entry.reason}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
