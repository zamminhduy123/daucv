"use client";

import { useState } from "react";
import LoadingOverlay from "@/components/workspace/LoadingOverlay";
import InterviewRoom from "@/components/workspace/InterviewRoom";
import InputSection from "@/components/workspace/InputSection";
import type { WorkspaceInputs } from "@/types";
import { sendInterviewChatAPI } from "@/lib/api";

const EMPTY_INPUTS: WorkspaceInputs = { jdText: "", cvText: "", cvFile: null };

const INTERVIEW_LOADING_MESSAGES = [
  "Nhận diện ngành nghề...",
  "Đối chiếu với kinh nghiệm...",
  "Chọn lọc kỹ năng trọng tâm...",
  "Sắp xong rồi ✨",
]

export default function InterviewPage() {
  const [currentView, setCurrentView] = useState<"input" | "interview">("input");
  const [inputs, setInputs] = useState<WorkspaceInputs>(EMPTY_INPUTS);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState("");
  const [interviewState, setInterviewState] = useState<unknown>(null);

  const handleChange = (patch: Partial<WorkspaceInputs>) =>
    setInputs((prev) => ({ ...prev, ...patch }));

  const handleInterview = async () => {
    if (!inputs.jdText.trim()) { setError("Bạn chưa dán JD vào nhé!"); return; }
    if (!inputs.cvText.trim()) {
      setError("Bạn chưa có nội dung CV — dán text hoặc tải PDF!");
      return;
    }
    setError("");
    setIsStarting(true);
    try {
      const data = await sendInterviewChatAPI(inputs.jdText, inputs.cvText, []);
      setInterviewState(data);
      setCurrentView("interview");
    } catch (err: unknown) {
      console.error(err);
      setError("Lỗi bắt đầu phỏng vấn. Vui lòng thử lại!");
      alert("Lỗi từ server: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsStarting(false);
    }
  };

  const handleBack = () => { setCurrentView("input"); setError(""); };

  return (
    <div className="relative">
      {isStarting && <LoadingOverlay messages={INTERVIEW_LOADING_MESSAGES} />}

      {currentView === "input" && (
        <InputSection
          inputs={inputs}
          onChange={handleChange}
          onAnalyze={() => {}}
          onInterview={handleInterview}
          isAnalyzing={false}
          isStartingInterview={isStarting}
          error={error}
        />
      )}

      {currentView === "interview" && (
        <InterviewRoom
          cvText={inputs.cvText}
          jdText={inputs.jdText}
          initialState={interviewState}
          onBack={handleBack}
        />
      )}
    </div>
  );
}
