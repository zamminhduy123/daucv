import React from "react";
import { CheckCircle2, AlertTriangle, Sparkles, Code, Lightbulb, Layers, MessageSquare, Users, FileText, Calendar, Clock, LayoutDashboard, ArrowRight } from "lucide-react";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts";
import Image from "next/image";

export interface SubScore {
  category: string;
  score: number;
  label: string;
}

export interface AIFeedbackSummary {
  positive: string;
  warning: string;
  actionable: string;
}

export interface TurnAnalysis {
  question: string;
  user_answer: string;
  feedback: string;
  ideal_answer_snippet: string;
}

export interface FinalInterviewReport {
  overall_score: number;
  overall_feedback: string;
  sub_scores: SubScore[];
  key_strengths: string[];
  areas_for_improvement: string[];
  top_topics_covered: string[];
  ai_feedback_summary: AIFeedbackSummary;
  turn_by_turn_analysis: TurnAnalysis[];
}

interface InterviewReportProps {
  report: FinalInterviewReport;
  onRetry: () => void;
  onHome: () => void;
}

export default function InterviewReport({ report, onRetry, onHome }: InterviewReportProps) {
  // Score color logic
  let scoreColor = "text-[#98C18E]";
  let scoreStroke = "stroke-[#98C18E]";
  let scoreBg = "stroke-green-50";
  
  if (report.overall_score < 65) {
    scoreColor = "text-orange-500";
    scoreStroke = "stroke-orange-500";
    scoreBg = "stroke-orange-50";
  } else if (report.overall_score < 85) {
    scoreColor = "text-yellow-500";
    scoreStroke = "stroke-yellow-500";
    scoreBg = "stroke-yellow-50";
  }

  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (report.overall_score / 100) * circumference;

  const categoryIcons: Record<string, React.ReactNode> = {
    "Kỹ năng chuyên môn": <Code size={24} className="text-emerald-600" />,
    "Giải quyết vấn đề": <Lightbulb size={24} className="text-amber-500" />,
    "Kiến thức ngành": <Layers size={24} className="text-blue-500" />,
    "Giao tiếp": <MessageSquare size={24} className="text-orange-500" />,
    "Thái độ & Hành vi": <Users size={24} className="text-teal-600" />
  };

  const categoryColors: Record<string, string> = {
    "Kỹ năng chuyên môn": "bg-emerald-50 text-emerald-600",
    "Giải quyết vấn đề": "bg-amber-50 text-amber-600",
    "Kiến thức ngành": "bg-blue-50 text-blue-600",
    "Giao tiếp": "bg-orange-50 text-orange-600",
    "Thái độ & Hành vi": "bg-teal-50 text-teal-600"
  };

  const today = new Date().toLocaleDateString("vi-VN", { year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="max-w-6xl mx-auto w-full pb-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 1. Top Header */}
      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4 md:p-8 mb-4 flex flex-col md:flex-row justify-between items-start md:items-center">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#2F4F4F]">Báo cáo Phỏng vấn</h1>
            <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-xs font-bold border border-green-200">Hoàn thành</span>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 font-medium mt-4">
            <span className="flex items-center gap-1.5"><Calendar size={16} /> {today}</span>
            <span className="flex items-center gap-1.5"><Clock size={16} /> ~15 phút</span>
            <span className="flex items-center gap-1.5"><LayoutDashboard size={16} /> Đậu Mock Interview</span>
          </div>
        </div>
        <div className="mt-6 md:mt-0 flex items-center bg-[#E8EFD5]/50 p-4 rounded-2xl border border-[#98C18E]/30 relative">
          <div className="mr-4 text-right">
            <p className="font-bold text-[#2F4F4F] text-sm">Bạn đã làm rất tốt!</p>
            <p className="text-xs text-gray-500">Hãy tiếp tục học hỏi và bạn sẽ còn tiến xa hơn nữa.</p>
          </div>
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-sm border border-green-100">
            <Image src="/main-icon.webp" alt="Bé Đậu" width={40} height={40} />
          </div>
        </div>
      </div>

      {/* 2. Scores Section */}
      <div className="grid grid-cols-1 lg:grid-cols-6 gap-2 mb-4">
        <div className="lg:col-span-2 bg-white rounded-3xl shadow-sm border border-gray-100 p-4 flex flex-col items-center justify-center text-center grid grid-cols-2 gap-2">
            <div className="relative w-full h-full">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
                <circle className={`${scoreBg} fill-none`} strokeWidth="10" cx="70" cy="70" r={radius} />
                <circle className={`${scoreStroke} fill-none transition-all duration-1000 ease-out`} strokeWidth="10" strokeLinecap="round" cx="70" cy="70" r={radius} style={{ strokeDasharray: circumference, strokeDashoffset }} />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-4xl font-black ${scoreColor}`}>{report.overall_score}</span>
                <span className="text-xs font-medium text-gray-500">/ 100</span>
            </div>
          </div>
          <div className="flex flex-col items-start">
            <h3 className="font-bold text-gray-400 text-xs uppercase tracking-wider mb-2">Overall Score</h3>
            <h2 className="text-xl font-bold text-green-700 mb-2">{report.overall_score >= 85 ? "Rất Tốt" : report.overall_score >= 65 ? "Khá Tốt" : "Cần Cố Gắng"}</h2>
            <p className="text-[10px] text-left text-gray-500 leading-relaxed max-w-[200px]">{report.overall_feedback}</p>
          </div>
        </div>
        
        <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-5 gap-4">
          {report.sub_scores?.map((sub, idx) => (
            <div key={idx} className="bg-white rounded-3xl shadow-sm border border-gray-100 p-5 flex flex-col items-center justify-center text-center">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-3 ${categoryColors[sub.category] || "bg-gray-50 text-gray-500"}`}>
                {categoryIcons[sub.category] || <Sparkles size={20} />}
              </div>
              <h4 className="text-[11px] font-bold text-gray-400 uppercase tracking-wide mb-2 h-8 flex items-center justify-center leading-tight">{sub.category}</h4>
              <p className="text-2xl font-black text-[#2F4F4F] mb-1">{sub.score}<span className="text-[10px] font-medium text-gray-400 ml-0.5">/100</span></p>
              <span className="text-xs font-medium px-2 py-1 bg-[#F9F9F2] rounded-md text-[#2F4F4F] border border-gray-100">{sub.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4 flex flex-col">
          <h3 className="font-bold text-[#2F4F4F] mb-2">Phân tích Kỹ năng</h3>
          <p className="text-sm text-gray-500 mb-4">Biểu đồ thể hiện mức độ hoàn thiện các kỹ năng</p>
          <div className="flex-1 min-h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={report.sub_scores}>
                <PolarGrid stroke="#f3f4f6" />
                <PolarAngleAxis dataKey="category" tick={{ fill: '#6b7280', fontSize: 11, fontWeight: 500 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="Score" dataKey="score" stroke="#98C18E" strokeWidth={2} fill="#98C18E" fillOpacity={0.35} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4 flex flex-col">
          <div className="mb-8">
            <h3 className="font-bold text-[#2F4F4F] mb-4">Chủ đề đã đề cập</h3>
            <div className="flex flex-wrap gap-2">
              {report.top_topics_covered?.map((topic, idx) => (
                <span key={idx} className="bg-[#E8EFD5] text-[#2F4F4F] px-3 py-1.5 rounded-full text-sm font-medium border border-[#98C18E]/30">{topic}</span>
              ))}
            </div>
          </div>
          
          <div className="mt-auto">
            <h3 className="font-bold text-[#2F4F4F] mb-4">Tổng quan</h3>
            <div className="space-y-0">
              <div className="flex justify-between items-center py-3 border-b border-gray-50">
                <span className="text-sm text-gray-500 flex items-center gap-2"><FileText size={16} className="text-gray-400"/> Tổng số câu hỏi</span>
                <span className="font-bold text-[#2F4F4F]">{report.turn_by_turn_analysis?.length || 0}</span>
              </div>
              <div className="flex justify-between items-center py-3 border-b border-gray-50">
                <span className="text-sm text-gray-500 flex items-center gap-2"><CheckCircle2 size={16} className="text-gray-400"/> Tỷ lệ hoàn thành</span>
                <span className="font-bold text-[#2F4F4F]">100%</span>
              </div>
              <div className="flex justify-between items-center py-3">
                <span className="text-sm text-gray-500 flex items-center gap-2"><Clock size={16} className="text-gray-400"/> Ước tính thời gian</span>
                <span className="font-bold text-[#2F4F4F]">15 phút</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Feedback Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-full bg-green-50 flex items-center justify-center text-green-600"><CheckCircle2 size={18} /></div>
            <h3 className="font-bold text-[#2F4F4F]">Điểm mạnh</h3>
          </div>
          <ul className="space-y-4">
            {report.key_strengths?.map((str, idx) => (
              <li key={idx} className="flex gap-3 ml-2 text-sm text-gray-600 leading-relaxed">
                <CheckCircle2 size={16} className="text-green-500 mt-0.5 shrink-0" />
                {str}
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-full bg-orange-50 flex items-center justify-center text-orange-500"><AlertTriangle size={18} /></div>
            <h3 className="font-bold text-[#2F4F4F]">Cần cải thiện</h3>
          </div>
          <ul className="space-y-4">
            {report.areas_for_improvement?.map((area, idx) => (
              <li key={idx} className="ml-2   flex gap-3 text-sm text-gray-600 leading-relaxed">
                <AlertTriangle size={16} className="text-orange-400 mt-0.5 shrink-0" />
                {area}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 5. AI Feedback & Next Steps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4">
          <h3 className="font-bold text-[#2F4F4F] mb-4 flex items-center gap-2"><Sparkles size={18} className="text-[#98C18E]"/> Phản hồi từ AI</h3>
          <div className="space-y-3">
            {report.ai_feedback_summary?.positive && (
              <div className="bg-green-50/70 border border-green-100 p-4 rounded-2xl flex gap-3">
                <CheckCircle2 size={18} className="text-green-600 shrink-0 mt-0.5" />
                <p className="text-sm text-green-800 leading-relaxed">{report.ai_feedback_summary.positive}</p>
              </div>
            )}
            {report.ai_feedback_summary?.warning && (
              <div className="bg-amber-50/70 border border-amber-100 p-4 rounded-2xl flex gap-3">
                <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
                <p className="text-sm text-amber-800 leading-relaxed">{report.ai_feedback_summary.warning}</p>
              </div>
            )}
            {report.ai_feedback_summary?.actionable && (
              <div className="bg-orange-50/70 border border-orange-100 p-4 rounded-2xl flex gap-3">
                <Lightbulb size={18} className="text-orange-600 shrink-0 mt-0.5" />
                <p className="text-sm text-orange-800 leading-relaxed">{report.ai_feedback_summary.actionable}</p>
              </div>
            )}
          </div>
        </div>
        
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-[#2F4F4F] mb-4">Gợi ý bước tiếp theo?</h3>
            <div className="space-y-4 mb-4">
              <div className="flex items-center gap-4 p-3 hover:bg-gray-50 rounded-xl transition-colors cursor-default border border-transparent hover:border-gray-100">
                <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center text-green-600"><FileText size={18} /></div>
                <div className="flex-1">
                  <p className="font-bold text-sm text-[#2F4F4F]">Xem lại câu trả lời</p>
                  <p className="text-xs text-gray-500">Xem chi tiết Q&A bên dưới để học hỏi</p>
                </div>
                <ArrowRight size={16} className="text-gray-400" />
              </div>
              <div className="flex items-center gap-4 p-3 hover:bg-gray-50 rounded-xl transition-colors cursor-default border border-transparent hover:border-gray-100">
                <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-orange-600"><Lightbulb size={18} /></div>
                <div className="flex-1">
                  <p className="font-bold text-sm text-[#2F4F4F]">Luyện tập kỹ năng yếu</p>
                  <p className="text-xs text-gray-500">Tập trung vào phần Cần cải thiện</p>
                </div>
                <ArrowRight size={16} className="text-gray-400" />
              </div>
            </div>
          </div>
          <button onClick={onRetry} className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white font-bold rounded-2xl shadow-sm transition-colors flex items-center justify-center gap-2 cursor-pointer">
            Bắt đầu Phỏng vấn mới
          </button>
        </div>
      </div>

      {/* 6. Transcript / Q&A */}
      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-4 md:p-8">
        <h3 className="font-bold text-[#2F4F4F] mb-4 text-xl">Chi tiết Câu hỏi & Trả lời</h3>
        <Accordion type="multiple" className="space-y-4">
          {report.turn_by_turn_analysis?.map((turn, idx) => (
            <AccordionItem key={idx} value={`turn-${idx}`} className="border border-gray-100 rounded-2xl overflow-hidden bg-white shadow-sm data-[state=open]:border-[var(--primary)]/30">
              <AccordionTrigger className="px-6 py-4 hover:no-underline hover:bg-gray-50 transition-colors [&[data-state=open]>div>h3]:text-[#98C18E]">
                <div className="flex flex-col items-start text-left gap-2">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Câu hỏi {idx + 1}</span>
                  <h3 className="text-[1.05rem] font-semibold text-[#2F4F4F] leading-snug">{turn.question}</h3>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-6 pb-6 pt-2 space-y-5">
                <div className="bg-[#F9F9F2] rounded-xl p-4 border border-gray-100">
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 block">Bạn đã trả lời:</span>
                  <p className="text-gray-700 leading-relaxed text-sm">{turn.user_answer}</p>
                </div>
                <div>
                  <span className="text-xs font-bold text-[#2F4F4F] uppercase tracking-wider mb-2 block">Nhận xét từ Bé Đậu:</span>
                  <p className="text-gray-700 leading-relaxed text-sm">{turn.feedback}</p>
                </div>
                <div className="bg-[#E8EFD5]/40 border-l-4 border-[#98C18E] p-4 rounded-r-xl">
                  <span className="text-xs font-bold text-[#5A9E40] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Sparkles size={14} /> Gợi ý trả lời ghi điểm
                  </span>
                  <p className="text-[#2F4F4F] leading-relaxed italic text-sm">{turn.ideal_answer_snippet}</p>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </div>
  );
}
