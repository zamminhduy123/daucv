"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Mail,
  Send,
  MessageCircle,
  Sparkles,
  Loader2,
  Copy,
  Check,
  Lightbulb,
  PenTool,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { generateWritingAPI } from "@/lib/api";

interface WriterResult {
  subject_line: string;
  content: string;
  tips: string[];
}

const WRITING_TYPES = [
  { id: "email", label: "Email ứng tuyển", icon: Mail, color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-200" },
  { id: "linkedin", label: "Tin nhắn LinkedIn", icon: Send, color: "text-sky-600", bg: "bg-sky-50", border: "border-sky-200" },
  { id: "zalo", label: "Tin nhắn Zalo cho HR", icon: MessageCircle, color: "text-green-600", bg: "bg-green-50", border: "border-green-200" },
  { id: "custom", label: "Yêu cầu khác...", icon: PenTool, color: "text-purple-600", bg: "bg-purple-50", border: "border-purple-200" },
] as const;

const TONES = ["Chuyên nghiệp", "Ngắn gọn", "Tự tin"];

export default function WriterPage() {
  const router = useRouter();
  const { cvText, jdText, hasData } = useWorkspace();

  const [writingType, setWritingType] = useState("email");
  const [tone, setTone] = useState("Chuyên nghiệp");
  const [customPrompt, setCustomPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<WriterResult | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  // Route guard
  useEffect(() => {
    if (!hasData) router.replace("/app/setup");
  }, [hasData, router]);

  const handleGenerate = async () => {
    setError("");
    setIsGenerating(true);
    setResult(null);
    try {
      const data = await generateWritingAPI({
        cv_text: cvText,
        jd_text: jdText,
        writing_type: writingType,
        tone,
        custom_prompt: writingType === "custom" ? customPrompt : undefined,
      });
      setResult(data);
    } catch (err: unknown) {
      console.error(err);
      setError("Lỗi tạo nội dung. Vui lòng thử lại!");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    const text = result.subject_line
      ? `Subject: ${result.subject_line}\n\n${result.content}`
      : result.content;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!hasData) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-7xl relative">
      {/* ── Left Column: Settings ── */}
      <motion.div
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        className="lg:col-span-4 sticky top-0 h-fit"
      >
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          {/* Header */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-9 h-9 bg-purple-50 rounded-xl flex items-center justify-center">
              <PenTool size={16} className="text-purple-600" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-[#2F4F4F]">Trợ lý Viết</h1>
              <p className="text-xs text-gray-400">Email, LinkedIn, Zalo & hơn thế</p>
            </div>
          </div>

          {/* Type selector */}
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Loại nội dung</p>
          <div className="flex flex-col gap-2 mb-6">
            {WRITING_TYPES.map(({ id, label, icon: Icon, color, bg, border }) => (
              <button
                key={id}
                onClick={() => setWritingType(id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all text-left border ${
                  writingType === id
                    ? `${bg} ${border} ${color}`
                    : "border-gray-100 text-gray-600 hover:bg-gray-50"
                }`}
              >
                <Icon size={16} className={writingType === id ? color : "text-gray-400"} />
                {label}
              </button>
            ))}
          </div>

          {/* Custom prompt textarea */}
          {writingType === "custom" && (
            <div className="mb-6">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Yêu cầu của bạn</p>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="VD: Viết thư cảm ơn sau phỏng vấn..."
                rows={3}
                className="w-full bg-gray-50 border border-gray-100 rounded-xl p-3 text-sm text-[#2F4F4F] outline-none resize-none focus:ring-2 focus:ring-[var(--primary)] transition-all"
              />
            </div>
          )}

          {/* Tone selector */}
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Giọng văn</p>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-sm text-[#2F4F4F] font-medium outline-none mb-6 focus:ring-2 focus:ring-[var(--primary)] transition-all"
          >
            {TONES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating || (writingType === "custom" && !customPrompt.trim())}
            className="w-full flex items-center justify-center gap-2 bg-[var(--primary)] text-white rounded-xl px-4 py-3 font-semibold text-sm hover:bg-[var(--primary)]/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Đang viết...
              </>
            ) : (
              <>
                <Sparkles size={16} />
                Tạo nội dung ✨
              </>
            )}
          </button>

          {error && (
            <p className="text-xs text-red-500 font-medium mt-3 text-center">{error}</p>
          )}
        </div>
      </motion.div>

      {/* ── Right Column: Result ── */}
      <motion.div
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1 }}
        className="lg:col-span-8"
      >
        {!result && !isGenerating && (
          <div className="bg-white rounded-3xl p-12 shadow-sm border border-gray-100 flex flex-col items-center justify-center text-center min-h-[400px]">
            <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mb-4">
              <PenTool size={28} className="text-gray-300" />
            </div>
            <p className="text-gray-400 text-sm max-w-xs leading-relaxed">
              Chọn loại nội dung và nhấn <strong className="text-[#2F4F4F]">Tạo</strong> để Bé Đậu viết giúp bạn.
            </p>
          </div>
        )}

        {isGenerating && (
          <div className="bg-white rounded-3xl p-12 shadow-sm border border-gray-100 flex flex-col items-center justify-center text-center min-h-[400px]">
            <Loader2 size={32} className="animate-spin text-[var(--primary)] mb-4" />
            <p className="text-gray-500 text-sm">Bé Đậu đang viết cho bạn...</p>
          </div>
        )}

        {result && !isGenerating && (
          <div className="bg-white rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 relative">
            {/* Subject line */}
            {result.subject_line && (
              <div className="mb-4">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Tiêu đề</span>
                <p className="text-lg font-bold text-[#2F4F4F] mt-1">{result.subject_line}</p>
              </div>
            )}

            {/* Content box */}
            <div className="relative group">
              <div className="bg-gray-50 p-5 rounded-xl whitespace-pre-wrap text-sm text-gray-700 leading-relaxed border border-gray-100">
                {result.content}
              </div>

              {/* Copy button */}
              <button
                onClick={handleCopy}
                className="absolute top-3 right-3 flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-50 hover:text-[#2F4F4F] transition-all shadow-sm opacity-0 group-hover:opacity-100 focus:opacity-100"
              >
                {copied ? (
                  <>
                    <Check size={12} className="text-green-500" />
                    Đã copy!
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    Copy
                  </>
                )}
              </button>
            </div>

            {/* Tips */}
            {result.tips?.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-100 p-4 rounded-xl mt-4 flex gap-3">
                <Lightbulb size={16} className="text-yellow-600 mt-0.5 flex-shrink-0" />
                <div className="flex flex-col gap-1.5">
                  {result.tips.map((tip, i) => (
                    <p key={i} className="text-xs text-yellow-800 leading-relaxed">{tip}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
}
