"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import InterviewRoom from "@/components/workspace/InterviewRoom";
import { sendInterviewChatAPI } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

const INTERVIEW_LOADING_MESSAGES = [
  "Nhận diện ngành nghề...",
  "Đối chiếu với kinh nghiệm...",
  "Chọn lọc kỹ năng trọng tâm...",
  "Sắp xong rồi ✨",
];

export default function InterviewPage() {
  const router = useRouter();
  const { cvText, jdText, hasData, cache, setCachedInterview } = useWorkspace();

  const [isStarting, setIsStarting] = useState(false);
  const [interviewState, setInterviewState] = useState<any>(
    cache.interviewState // Initialize from cache
  );
  const [totalQuestions, setTotalQuestions] = useState(5);
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

  // Auto-start is disabled because we now have a setup screen
  // User must click "Bắt đầu phỏng vấn" which calls startNow()


  const handleBack = () => {
    // Clear interview state and return to setup screen
    hasTriggered.current = false;
    setInterviewState(null);
    setCachedInterview(null);
    setIsSettingUp(true);
  };

  if (!hasData) return null; // Will redirect via useEffect

  const startNow = () => {
    setIsSettingUp(false);
    hasTriggered.current = true;
    setIsStarting(true);
    setError("");
    sendInterviewChatAPI(jdText, cvText, [], 1, totalQuestions)
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
        <div className="flex flex-col items-center justify-center min-h-[60vh] py-10 px-4 animate-in fade-in zoom-in-95 duration-500">
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 max-w-md w-full text-center">
            <div className="w-16 h-16 bg-green-50 text-(--primary) rounded-2xl flex items-center justify-center mx-auto mb-6">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><circle cx="10" cy="13" r="2"/><path d="m20 17-1.83-1.83"/></svg>
            </div>
            <h2 className="text-2xl font-bold text-[#2F4F4F] mb-2">Sẵn sàng phỏng vấn?</h2>
            <p className="text-gray-500 mb-8">Chọn số lượng câu hỏi để Đậu chuẩn bị kịch bản phù hợp nhất cho bạn.</p>
            
            <div className="space-y-3 mb-8 text-left">
              {[
                { value: 3, label: "Phỏng vấn nhanh", desc: "3 câu hỏi trọng tâm" },
                { value: 5, label: "Tiêu chuẩn", desc: "5 câu hỏi (Khuyên dùng)" },
                { value: 7, label: "Chuyên sâu", desc: "7 câu hỏi chi tiết" },
              ].map((opt) => (
                <label key={opt.value} className={`flex items-center gap-4 p-4 rounded-2xl border-2 cursor-pointer transition-all ${totalQuestions === opt.value ? 'border-(--primary) bg-green-50/30' : 'border-gray-100 hover:border-green-100'}`}>
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
        <InterviewRoom
          cvText={cvText}
          jdText={jdText}
          initialState={interviewState}
          totalQuestions={totalQuestions}
          onBack={handleBack}
        />
      )}
    </div>
  );
}
