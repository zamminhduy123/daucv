import { Sparkles, HelpCircle, ArrowDown } from "lucide-react";
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
      <div className="bg-white rounded-3xl p-4 sm:p-8 border-2 border-(--primary)/10 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-(--primary)/10 rounded-xl flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-(--primary)" />
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
              className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden flex flex-col mb-6"
            >
              <div className="flex flex-col md:grid md:grid-cols-2 md:divide-x divide-gray-100">
                {/* Original */}
                <div className="flex flex-col bg-red-50/30 p-4 sm:p-6 relative">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
                    <div className="w-2 h-2 rounded-full bg-red-500"></div>
                    Bản gốc
                  </div>
                  <p className="text-sm text-gray-500 line-through opacity-80 leading-relaxed">
                    {entry.original_text}
                  </p>
                  
                  {/* Mobile Mobile Visual Connector */}
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 z-10 w-8 h-8 bg-white border border-gray-100 rounded-full flex items-center justify-center text-gray-400 shadow-sm md:hidden">
                    <ArrowDown size={14} />
                  </div>
                </div>

                {/* Upgraded */}
                <div className="flex flex-col bg-green-50/30 p-4 sm:p-6 pt-8 md:pt-6">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
                    <div className="w-2 h-2 rounded-full bg-brand-primary"></div>
                    Bản nâng cấp
                  </div>
                  <p
                    className="text-sm text-gray-800 leading-relaxed [&>strong]:font-semibold [&>strong]:text-brand-text [&>strong]:bg-green-100/50 [&>strong]:px-1 [&>strong]:rounded"
                    dangerouslySetInnerHTML={{ __html: entry.upgraded_text }}
                  />
                </div>
              </div>

              {/* Insight Footer */}
              <div className="bg-slate-50 border-t border-gray-100 p-4 sm:px-6 sm:py-4 flex items-start gap-3 w-full">
                <HelpCircle size={16} className="shrink-0 mt-0.5 text-gray-400" />
                <p className="text-sm text-gray-600 leading-relaxed">{entry.reason}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
