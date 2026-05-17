"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import InterviewRoomMinimal from "@/components/workspace/InterviewRoomMinimal";
import type { InterviewState } from "@/components/workspace/InterviewRoomMinimal";
import { sendInterviewChatAPI } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

const INTERVIEW_LOADING_MESSAGES = [
  "Nhận diện ngành nghề...",
  "Đối chiếu với kinh nghiệm...",
  "Chọn lọc kỹ năng trọng tâm...",
  "Sắp xong rồi ✨",
];

type InterviewType = "hr" | "technical" | "manager" | "general";

const INTERVIEW_TYPES: {
  value: InterviewType;
  emoji: string;
  label: string;
  desc: string;
  color: string;
  border: string;
  bg: string;
}[] = [
  {
    value: "general",
    emoji: "🎯",
    label: "Tổng hợp",
    desc: "Kết hợp hành vi, chuyên môn và văn hoá",
    color: "text-[var(--primary)]",
    border: "border-(--primary)",
    bg: "bg-green-50/40",
  },
  {
    value: "hr",
    emoji: "🤝",
    label: "Nhân sự (HR)",
    desc: "Hành vi, văn hóa công ty, deal lương",
    color: "text-violet-600",
    border: "border-violet-400",
    bg: "bg-violet-50/40",
  },
  {
    value: "technical",
    emoji: "💻",
    label: "Chuyên môn",
    desc: "Kỹ năng cứng, công nghệ, giải quyết vấn đề",
    color: "text-blue-600",
    border: "border-blue-400",
    bg: "bg-blue-50/40",
  },
  {
    value: "manager",
    emoji: "📊",
    label: "Quản lý (Line Manager)",
    desc: "Tư duy làm việc, quản lý rủi ro, impact",
    color: "text-amber-600",
    border: "border-amber-400",
    bg: "bg-amber-50/40",
  },
];

export default function InterviewPage() {
  const router = useRouter();
  const { cvText, jdText, hasData, cache, setCachedInterview } = useWorkspace();

  const [isStarting, setIsStarting] = useState(false);
  const [interviewState, setInterviewState] = useState<InterviewState | null>(
    cache.interviewState as InterviewState | null // Initialize from cache
  );
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [interviewType, setInterviewType] = useState<InterviewType>("general");
  const [error, setError] = useState("");
  const hasTriggered = useRef(false);

  // Track if we are in the "setup" phase of the interview
  const [isSettingUp, setIsSettingUp] = useState(!cache.interviewState);

  // Route guard: redirect if no data
  useEffect(() => {
    if (!hasData) {
      router.replace("/app/setup");
    }
  }, [hasData, router]);

  const handleBack = () => {
    hasTriggered.current = false;
    setInterviewState(null);
    setCachedInterview(null);
    setIsSettingUp(true);
  };

  if (!hasData) return null;

  const startNow = () => {
    setIsSettingUp(false);
    hasTriggered.current = true;
    setIsStarting(true);
    setError("");
    sendInterviewChatAPI(jdText, cvText, [], 1, totalQuestions, interviewType)
      .then((data) => {
        setInterviewState(data);
        setCachedInterview(data);
      })
      .catch((err) => {
        console.error(err);
        setError("Lỗi bắt đầu phỏng vấn. Vui lòng thử lại!");
      })
      .finally(() => {
        setIsStarting(false);
      });
  };

  return (
    <div className="relative">
      {isStarting && <LoadingOverlay messages={INTERVIEW_LOADING_MESSAGES} />}

      {error && !isStarting && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-600 font-medium">{error}</p>
          <button
            onClick={() => {
              hasTriggered.current = false;
              setInterviewState(null);
              setError("");
              setIsSettingUp(true);
            }}
            className="px-6 py-3 bg-[var(--primary)] text-white rounded-2xl font-semibold hover:scale-105 transition-all"
          >
            Thử lại
          </button>
        </div>
      )}

      {isSettingUp && !isStarting && !error && (
        <div className="flex flex-col items-center justify-center animate-in fade-in zoom-in-95 duration-500">
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 w-full">

            {/* Header icon + title */}
            <div className="flex flex-col items-center text-center mb-8">
              <div className="w-16 h-16 bg-green-50 text-(--primary) rounded-2xl flex items-center justify-center mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><circle cx="10" cy="13" r="2"/><path d="m20 17-1.83-1.83"/></svg>
              </div>
              <h2 className="text-2xl font-bold text-[#2F4F4F] mb-1">Sẵn sàng phỏng vấn?</h2>
              <p className="text-gray-500 text-sm">Chọn vòng phỏng vấn và số câu hỏi phù hợp.</p>
            </div>

            {/* ── Interview Type ── */}
            <div className="grid grid-cols-1 gap-8 sm:gap-12 mb-8 sm:grid-cols-2">
              <div className="relative flex flex-col gap-2">
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest ">
                  Vòng phỏng vấn
                </p>
                <div className="grid grid-cols-2 gap-3">
                  {INTERVIEW_TYPES.map((opt) => {
                    const selected = interviewType === opt.value;
                    return (
                      <button
                        key={opt.value}
                        onClick={() => setInterviewType(opt.value)}
                        className={`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 text-left transition-all duration-200 cursor-pointer
                          ${selected
                            ? `${opt.border} ${opt.bg} shadow-sm`
                            : "border-gray-100 hover:border-gray-200 bg-gray-50/30"
                          }`}
                      >
                        <span className="text-2xl">{opt.emoji}</span>
                        <span className={`font-semibold text-sm leading-tight ${selected ? opt.color : "text-[#2F4F4F]"}`}>
                          {opt.label}
                        </span>
                        <span className="text-[11px] text-gray-400 leading-snug">{opt.desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* ── Question Count ── */}
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
                  Số câu hỏi
                </p>
                <div className="space-y-3 text-left">
                  {[
                    { value: 3, label: "Phỏng vấn nhanh", desc: "3 câu hỏi trọng tâm" },
                    { value: 5, label: "Tiêu chuẩn", desc: "5 câu hỏi (Khuyên dùng)" },
                    { value: 7, label: "Chuyên sâu", desc: "7 câu hỏi chi tiết" },
                  ].map((opt) => (
                    <label
                      key={opt.value}
                      className={`flex items-center gap-4 p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                        totalQuestions === opt.value
                          ? "border-(--primary) bg-green-50/30"
                          : "border-gray-100 hover:border-green-100"
                      }`}
                    >
                      <input
                        type="radio"
                        name="totalQuestions"
                        value={opt.value}
                        checked={totalQuestions === opt.value}
                        onChange={() => setTotalQuestions(opt.value)}
                        className="w-5 h-5 text-(--primary) border-gray-300 focus:ring-(--primary)"
                      />
                      <div>
                        <div className="font-semibold text-[#2F4F4F]">{opt.label}</div>
                        <div className="text-sm text-gray-500">{opt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={startNow}
              className="w-full py-4 bg-(--primary) text-white font-bold rounded-2xl shadow-md hover:bg-[#4d8636] transition-colors"
            >
              Bắt đầu phỏng vấn
            </button>
          </div>
        </div>
      )}

      {!!interviewState && !isStarting && !isSettingUp && (
        <InterviewRoomMinimal
          cvText={cvText}
          jdText={jdText}
          initialState={interviewState}
          totalQuestions={totalQuestions}
          interviewType={interviewType}
          onBack={handleBack}
        />
      )}
    </div>
  );
}
