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
  const [interviewState, setInterviewState] = useState<unknown>(
    cache.interviewState // Initialize from cache
  );
  const [error, setError] = useState("");
  const hasTriggered = useRef(false);

  // Route guard: redirect if no data
  useEffect(() => {
    if (!hasData) {
      router.replace("/app/setup");
    }
  }, [hasData, router]);

  // Auto-start interview on mount (only once, skip if cached)
  useEffect(() => {
    if (!hasData || hasTriggered.current || interviewState) return;
    hasTriggered.current = true;

    const startInterview = async () => {
      setIsStarting(true);
      setError("");
      try {
        const data = await sendInterviewChatAPI(jdText, cvText, []);
        setInterviewState(data);
        setCachedInterview(data); // Save to cache
      } catch (err: unknown) {
        console.error(err);
        setError("Lỗi bắt đầu phỏng vấn. Vui lòng thử lại!");
      } finally {
        setIsStarting(false);
      }
    };

    startInterview();
  }, [hasData, cvText, jdText, interviewState, setCachedInterview]);

  const handleBack = () => {
    router.push("/app/setup");
  };

  if (!hasData) return null; // Will redirect via useEffect

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
            }}
            className="px-6 py-3 bg-[var(--primary)] text-white rounded-2xl font-semibold hover:scale-105 transition-all"
          >
            Thử lại
          </button>
        </div>
      )}

      {interviewState && !isStarting && (
        <InterviewRoom
          cvText={cvText}
          jdText={jdText}
          initialState={interviewState}
          onBack={handleBack}
        />
      )}
    </div>
  );
}
