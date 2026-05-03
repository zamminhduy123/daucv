import { Pen, ArrowRight, ArrowDown } from "lucide-react";
import type { SuggestedEdit } from "@/types";
import { motion } from "framer-motion";

export default function DiffViewer({ edits }: { edits: SuggestedEdit[] }) {
  if (!edits || edits.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="mb-8"
    >
      <div className="bg-white border border-gray-100 rounded-3xl p-6 md:p-8 shadow-sm">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 bg-purple-50 rounded-xl flex items-center justify-center">
            <Pen size={16} className="text-purple-500" />
          </div>
          <h2 className="text-base font-bold text-[#2F4F4F]">Suggested Rewrite</h2>
        </div>

        {/* Edit entries */}
        <div className="flex flex-col gap-5">
          {edits.map((entry, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.08 }}
              className="flex flex-col gap-4"
            >
              {/* Side-by-side cards */}
              <div className="flex flex-col md:flex-row md:items-stretch gap-2">
                {/* Original card */}
                <div className="flex-1 border border-gray-100 rounded-2xl p-5 bg-gray-50">
                  <span className="text-[11px] uppercase tracking-wider text-gray-700 mb-2.5 block font-bold">
                    Original
                  </span>
                  <p className="text-sm text-gray-500 leading-relaxed">
                    {entry.original_text}
                  </p>
                </div>

                {/* Arrow connector */}
                <div className="flex items-center justify-center flex-shrink-0">
                  {/* Desktop horizontal arrow */}
                  <div className="hidden md:flex w-8 h-8 items-center justify-center">
                    <ArrowRight size={18} className="text-green-400" />
                  </div>
                  {/* Mobile vertical arrow */}
                  <div className="flex md:hidden w-8 h-8 items-center justify-center mx-auto">
                    <ArrowDown size={18} className="text-green-400" />
                  </div>
                </div>

                {/* Improved card */}
                <div className="flex-1 bg-green-50/60 border border-green-100 rounded-2xl p-5">
                  <span className="inline-block text-[11px] font-semibold uppercase tracking-wider text-green-600 bg-green-100/80 px-2 py-0.5 rounded mb-2.5">
                    Edit Suggestion
                  </span>
                  <p
                    className="text-sm text-gray-800 font-semibold leading-relaxed [&>strong]:font-bold [&>strong]:text-[#2F4F4F]"
                    dangerouslySetInnerHTML={{ __html: entry.upgraded_text }}
                  />
                  {/* Reason — inline under improved text */}
                  {entry.reason && (
                    <p className="mt-3 text-xs text-gray-400 leading-relaxed">
                      <span className="font-semibold text-gray-500">Why this is better:</span>{" "}
                      {entry.reason}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
