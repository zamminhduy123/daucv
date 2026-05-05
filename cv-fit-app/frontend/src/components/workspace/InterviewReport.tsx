import React from "react";
import { CheckCircle2, AlertTriangle, ArrowRight, RotateCcw, Home, ChevronDown, Sparkles } from "lucide-react";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";

interface TurnAnalysis {
  question: string;
  user_answer: string;
  feedback: string;
  ideal_answer_snippet: string;
}

export interface FinalInterviewReport {
  overall_score: number;
  overall_feedback: string;
  key_strengths: string[];
  areas_for_improvement: string[];
  turn_by_turn_analysis: TurnAnalysis[];
}

interface InterviewReportProps {
  report: FinalInterviewReport;
  onRetry: () => void;
  onHome: () => void;
}

export default function InterviewReport({ report, onRetry, onHome }: InterviewReportProps) {
  // Determine color for the score circle
  let scoreColor = "text-green-500";
  let scoreStroke = "stroke-green-500";
  let scoreBg = "stroke-green-100";
  
  if (report.overall_score < 65) {
    scoreColor = "text-orange-500";
    scoreStroke = "stroke-orange-500";
    scoreBg = "stroke-orange-100";
  } else if (report.overall_score < 85) {
    scoreColor = "text-yellow-500";
    scoreStroke = "stroke-yellow-500";
    scoreBg = "stroke-yellow-100";
  }

  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (report.overall_score / 100) * circumference;

  return (
    <div className="max-w-5xl mx-auto w-full p-4 md:p-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        
        {/* Header Section */}
        <div className="p-8 md:p-12 text-center relative border-b border-gray-100 bg-gradient-to-b from-[#F9F9F2] to-white">
          <h1 className="text-3xl md:text-4xl font-extrabold text-[#2F4F4F] mb-6">Kết quả phỏng vấn</h1>
          
          <div className="relative w-40 h-40 mx-auto mb-6">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
              <circle
                className={`${scoreBg} fill-none`}
                strokeWidth="12"
                cx="70"
                cy="70"
                r={radius}
              />
              <circle
                className={`${scoreStroke} fill-none transition-all duration-1000 ease-out`}
                strokeWidth="12"
                strokeLinecap="round"
                cx="70"
                cy="70"
                r={radius}
                style={{ strokeDasharray: circumference, strokeDashoffset }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-4xl font-black ${scoreColor}`}>
                {report.overall_score}
              </span>
              <span className="text-sm font-medium text-gray-500">/ 100</span>
            </div>
          </div>
          
          <p className="text-lg text-gray-700 max-w-2xl mx-auto leading-relaxed">
            {report.overall_feedback}
          </p>
        </div>

        {/* 2-Column Summary */}
        <div className="p-6 md:p-10 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Strengths */}
          <div className="bg-green-50/50 border border-green-100 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-green-100 rounded-lg text-green-600">
                <CheckCircle2 size={24} />
              </div>
              <h2 className="text-xl font-bold text-[#2F4F4F]">Điểm mạnh</h2>
            </div>
            <ul className="space-y-3">
              {report.key_strengths.map((strength, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="text-green-500 mt-0.5 shrink-0" />
                  <span className="text-gray-700 leading-relaxed">{strength}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Improvements */}
          <div className="bg-orange-50/50 border border-orange-100 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-orange-100 rounded-lg text-orange-600">
                <AlertTriangle size={24} />
              </div>
              <h2 className="text-xl font-bold text-[#2F4F4F]">Cần cải thiện</h2>
            </div>
            <ul className="space-y-3">
              {report.areas_for_improvement.map((area, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <AlertTriangle size={18} className="text-orange-500 mt-0.5 shrink-0" />
                  <span className="text-gray-700 leading-relaxed">{area}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Turn-by-turn Analysis */}
        <div className="p-6 md:p-10 border-t border-gray-100">
          <h2 className="text-2xl font-bold text-[#2F4F4F] mb-6 flex items-center gap-2">
            Phân tích chi tiết <span className="text-gray-400 font-normal text-lg">({report.turn_by_turn_analysis.length} câu hỏi)</span>
          </h2>

          <Accordion type="multiple" className="space-y-4">
            {report.turn_by_turn_analysis.map((turn, idx) => (
              <AccordionItem key={idx} value={`turn-${idx}`} className="border border-gray-200 rounded-2xl overflow-hidden bg-white shadow-sm data-[state=open]:border-(--primary)/30">
                <AccordionTrigger className="px-6 py-4 hover:no-underline hover:bg-gray-50 transition-colors [&[data-state=open]>div>h3]:text-(--primary)">
                  <div className="flex flex-col items-start text-left gap-2">
                    <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Câu hỏi {idx + 1}</span>
                    <h3 className="text-[1.05rem] font-semibold text-[#2F4F4F] leading-snug">{turn.question}</h3>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-6 pt-2 space-y-5">
                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                    <span className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 block">Bạn đã trả lời:</span>
                    <p className="text-gray-700 leading-relaxed">{turn.user_answer}</p>
                  </div>
                  
                  <div>
                    <span className="text-xs font-bold text-[#2F4F4F] uppercase tracking-wider mb-2 block">Nhận xét từ Bé Đậu:</span>
                    <p className="text-gray-700 leading-relaxed">{turn.feedback}</p>
                  </div>

                  <div className="bg-[#E8EFD5]/40 border-l-4 border-[#5A9E40] p-4 rounded-r-xl">
                    <span className="text-xs font-bold text-[#5A9E40] uppercase tracking-wider mb-1 block flex items-center gap-1.5">
                      <Sparkles size={14} /> Gợi ý trả lời ghi điểm
                    </span>
                    <p className="text-[#2F4F4F] leading-relaxed italic">{turn.ideal_answer_snippet}</p>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>

        {/* Bottom Actions */}
        <div className="p-6 md:p-10 bg-gray-50 border-t border-gray-100 flex flex-col sm:flex-row gap-4 justify-end items-center">
          <button 
            onClick={onHome}
            className="flex items-center gap-2 px-6 py-3 font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            <Home size={18} />
            Quay về Dashboard
          </button>
          <button 
            onClick={onRetry}
            className="flex items-center gap-2 px-8 py-3 bg-[var(--primary)] text-white font-semibold rounded-xl shadow-sm hover:scale-105 transition-transform"
          >
            <RotateCcw size={18} />
            Luyện tập lại
          </button>
        </div>

      </div>
    </div>
  );
}
