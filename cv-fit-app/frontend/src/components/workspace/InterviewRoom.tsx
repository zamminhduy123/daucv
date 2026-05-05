"use client";

// Web Speech API type declarations
// declare class SpeechRecognition extends EventTarget {
//   lang: string;
//   continuous: boolean;
//   onresult: ((e: SpeechRecognitionEvent) => void) | null;
//   onend: (() => void) | null;
//   start(): void;
//   stop(): void;
// }
// declare class SpeechRecognitionEvent extends Event {
//   results: SpeechRecognitionResultList;
// }

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { PhoneOff, Target, Sparkles, BrainCircuit, Activity, Zap, Lightbulb, AudioLines, Send, X, Volume2, VolumeX } from "lucide-react";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useInterviewApi, Message } from "@/hooks/useInterviewApi";
import SupportCard from "@/components/workspace/SupportCard";
import { useTTS } from "@/hooks/useTTS";
import { finishInterviewAPI } from "@/lib/api";
import InterviewReport, { FinalInterviewReport } from "./InterviewReport";
import LoadingOverlay from "./LoadingOverlay";
import { useWorkspace } from "@/context/WorkspaceContext";

// Initial Mock Data
interface InterviewRoomProps {
  cvText: string;
  jdText: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  initialState: any;
  totalQuestions: number;
  onBack: () => void;
}

export default function InterviewRoom({ cvText, jdText, initialState, totalQuestions, onBack }: InterviewRoomProps) {
  const { setCachedInterview } = useWorkspace();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showSupportPopup, setShowSupportPopup] = useState(false);
  const [hasShownSupportPopup, setHasShownSupportPopup] = useState(false);
  
  const isResuming = !!initialState?.messages;

  const initialMessages: Message[] = isResuming 
    ? initialState.messages
    : initialState?.next_question ? [
        { role: "assistant" as const, content: initialState.next_question, hint_for_user: initialState.hint_for_user }
      ] : [];

  const { messages, loading, liveMetrics, sendMessage, setMessages } = useInterviewApi(
    initialMessages, 
    isResuming ? initialState.liveMetrics : initialState?.metrics
  );
  
  const { voiceEnabled, setVoiceEnabled, speak, stopSpeaking, isSpeaking, isLoading: isLoadingTTS } = useTTS();
  const [currentQuestion, setCurrentQuestion] = useState(isResuming ? initialState.currentQuestion : 1);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [report, setReport] = useState<FinalInterviewReport | null>(isResuming ? initialState.report : null);
  const prevMessagesLength = useRef(messages.length);

  const {
    isListening,
    transcript,
    setTranscript,
    interimTranscript,
    hasBrowserSupport,
    startListening,
    stopListening,
  } = useSpeechRecognition();

  // Scroll to bottom when messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Sync state to Workspace cache so it persists when switching tabs
  useEffect(() => {
    if (messages.length > 0) {
      setCachedInterview({
        ...initialState,
        messages,
        currentQuestion,
        liveMetrics,
        report
      });
    }
  }, [messages, currentQuestion, liveMetrics, report, setCachedInterview, initialState]);

  // Speak assistant's latest question out loud when it arrives (Vietnamese)
  useEffect(() => {
    // Only auto-speak if a NEW assistant message was added
    // This prevents re-speaking when switching tabs/remounting
    if (messages.length > prevMessagesLength.current) {
      const latestAssistant = [...messages].reverse().find((m) => m.role === "assistant");
      if (latestAssistant?.content) {
        speak(latestAssistant.content);
      }
    }
    prevMessagesLength.current = messages.length;
  }, [messages, speak]);

  // Clean up on unmount handled by hook

  const userMessagesCount = messages.filter((msg) => msg.role === "user").length;
  const assistantMessagesCount = messages.filter((msg) => msg.role === "assistant").length;

  useEffect(() => {
    if (hasShownSupportPopup) return;

    const firstQuestionCompleted = userMessagesCount >= 1 && assistantMessagesCount >= 2 && !loading;

    if (firstQuestionCompleted) {
      setShowSupportPopup(true);
      setHasShownSupportPopup(true);
    }
  }, [assistantMessagesCount, hasShownSupportPopup, loading, userMessagesCount]);

  // Handle actual API Call
  const handleSendMessage = async () => {
    const textToSend = transcript.trim();
    if (!textToSend || loading || isGeneratingReport) return;
    
    // reset input
    setTranscript("");
    
    if (currentQuestion >= totalQuestions) {
      // This is the answer to the final question
      setIsGeneratingReport(true);
      
      // Add user message to UI immediately
      const finalMsg: Message = { role: "user", content: textToSend };
      const fullHistory = [...messages, finalMsg];
      setMessages(fullHistory);

      try {
        const data = await finishInterviewAPI(
          jdText, 
          cvText, 
          fullHistory.map(m => ({ role: m.role, content: m.content }))
        );
        setReport(data);
      } catch (err) {
        console.error(err);
        alert("Lỗi khi tạo báo cáo kết quả. Vui lòng thử lại!");
      } finally {
        setIsGeneratingReport(false);
      }
    } else {
      // Call the custom hook function with the next question number
      const nextQ = currentQuestion + 1;
      sendMessage(textToSend, jdText, cvText, nextQ, totalQuestions);
      setCurrentQuestion(nextQ);
    }
  };

  const toggleMic = () => {
    if (!hasBrowserSupport) { 
      alert("Trình duyệt không hỗ trợ nhận diện giọng nói."); 
      return; 
    }
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const endInterview = () => {
    onBack();
  };

  const resetInterview = () => {
    onBack(); // Just go back to setup to restart for now
  };

  const latestHint = (messages.length > 0 && messages[messages.length - 1].role === "assistant")
    ? messages[messages.length - 1].hint_for_user || "Đang đợi câu hỏi..."
    : "Đang đợi câu hỏi...";

  if (report) {
    return (
      <>
        <InterviewReport report={report} onRetry={resetInterview} onHome={endInterview} />
      </>
    );
  }

  return (
    <div className="h-screen py-1 md:py-2 px-1 w-full bg-[#F9F9F2] text-[#2F4F4F] font-sans overflow-hidden flex flex-col gap-3">
      {isGeneratingReport && <LoadingOverlay messages={["Đang tổng hợp kết quả...", "Phân tích điểm mạnh, điểm yếu...", "Đánh giá mức độ phù hợp JD...", "Sắp xong rồi! 🚀"]} />}

      {showSupportPopup && (
        <div className="shrink-0 w-full px-1">
          <div className="relative mx-auto">
            <button
              type="button"
              onClick={() => setShowSupportPopup(false)}
              className="absolute right-2 top-2 z-10 h-6 w-6 rounded-full bg-white/90 text-[#5A6D6D] shadow-sm hover:bg-white transition-colors flex items-center justify-center"
              title="Đóng"
            >
              <X size={14} />
            </button>
            <SupportCard compact />
          </div>
        </div>
      )}

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-3">
      {/* 1. MAIN CENTER AREA: Conversation (75%) */}
  <main className="flex-1 flex flex-col bg-white rounded-2xl md:rounded-3xl shadow-sm border border-[#2F4F4F]/5 relative overflow-hidden h-full">
        
        {/* Header Avatar: Smoother on mobile */}
        <header className="py-3 md:py-3.5 border-b border-[#2F4F4F]/5 flex items-center justify-between px-3 md:px-6 shrink-0 bg-white z-10 shadow-sm relative">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="relative w-8 h-8 rounded-full bg-[#E8EFD5] shadow-sm flex items-center justify-center shrink-0">
              <Image src="/main-icon.webp" alt="Bé Đậu" width={16} height={16} />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] md:text-xs font-semibold text-(--primary) uppercase tracking-wider truncate">
                {isListening 
                  ? "Bé Đậu đang nghe..." 
                  : loading 
                    ? "Bé Đậu đang nghĩ..." 
                    : isLoadingTTS
                      ? "Bé Đậu đang chuẩn bị giọng nói..."
                      : isSpeaking
                        ? "Bé Đậu đang nói..."
                        : "Bé Đậu đang sẵn sàng"}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="text-[10px] md:text-[11px] text-gray-500 font-medium">Câu hỏi {currentQuestion} / {totalQuestions}</div>
                <div className="w-24 md:w-32 h-1.5 bg-gray-100 rounded-full overflow-hidden shrink-0">
                  <div 
                    className="h-full bg-(--primary) transition-all duration-300" 
                    style={{ width: `${(currentQuestion / totalQuestions) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={endInterview}
            className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors shrink-0 flex items-center gap-2 text-sm font-medium border border-transparent hover:border-red-100"
            title="Kết thúc"
          >
            <span className="hidden md:inline">Thoát</span>
            <PhoneOff size={18} />
          </button>
        </header>

        {/* Transcript Area: Tighter padding on mobile */}
        <div className="flex-1 overflow-y-auto p-3 md:p-6 space-y-4 md:space-y-6 bg-[#FAFAFA] custom-scrollbar pb-28 md:pb-32">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"} max-w-[90%] md:max-w-[85%] ${msg.role === "user" ? "ml-auto" : "mr-auto"}`}>
              {/* Chat Bubble */}
              <div 
                className={`p-3 md:p-4 rounded-xl md:rounded-2xl text-[0.92rem] md:text-[1rem] leading-relaxed shadow-sm relative group
                  ${msg.role === "assistant" 
                    ? "bg-[#E8EFD5] text-[#2F4F4F] rounded-tl-sm border border-(--primary)/20" 
                    : "bg-white text-[#2F4F4F] rounded-tr-sm border border-gray-200"
                  }`}
              >
                {msg.content}
                
                {msg.role === "assistant" && (
                  <button
                    onClick={() => speak(msg.content)}
                    className="absolute -right-8 top-1/2 -translate-y-1/2 p-1.5 text-[#5A6D6D] hover:text-(--primary) opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Nghe lại"
                  >
                    <Volume2 size={16} />
                  </button>
                )}
              </div>

              {/* Unique 2026 AI Insiinterght Card for User Messages */}
              {msg.role === "user" && msg.feedback && (
                <div className="mt-2 bg-blue-50 border border-(--primary)/20 text-[#2F4F4F] text-[0.78rem] md:text-sm p-2 md:p-3 rounded-xl flex items-start gap-2 md:gap-3 shadow-sm mr-2">
                  <span className="text-sm md:text-xl">💡</span>
                  <p className="leading-snug">{msg.feedback}</p>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex flex-col items-start mr-auto max-w-[85%] animate-in fade-in slide-in-from-left-2 duration-300">
              <div className="p-3 md:p-4 rounded-xl md:rounded-2xl bg-[#E8EFD5] text-[#2F4F4F] rounded-tl-sm border border-(--primary)/20 shadow-sm flex items-center gap-3">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 bg-[#2F4F4F]/40 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="w-2 h-2 bg-[#2F4F4F]/40 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="w-2 h-2 bg-[#2F4F4F]/40 rounded-full animate-bounce"></span>
                </div>
                <span className="text-sm font-medium italic opacity-80">Bé Đậu đang suy nghĩ...</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
          <div className="h-24 md:h-28 shrink-0" />
        </div>

        {/* Bottom Floating Console: redesigned like reference */}
        <div className="absolute bottom-2.5 md:bottom-3 left-1/2 -translate-x-1/2 w-[97%] md:w-[90%] rounded-xl border border-gray-300/90 border-dashed bg-[#F6F6F4] shadow-lg p-3 md:p-4 z-20 flex justify-between">

          <textarea
            value={isListening ? (transcript + (interimTranscript ? (transcript ? " " : "") + interimTranscript : "")) : transcript}
            onChange={(e) => setTranscript(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!isListening) handleSendMessage();
              }
            }}
            placeholder={isListening ? "Listening..." : "Reply..."}
            className="w-full bg-transparent border-none outline-none text-sm sm:text-sm text-[#2F4F4F] placeholder:text-[#666D75] resize-none leading-relaxed min-h-9 max-h-[40vh] custom-scrollbar overflow-y-auto mr-4"
            rows={transcript || interimTranscript ? Math.min(10, (transcript + " " + interimTranscript).split("\n").length + Math.floor((transcript + interimTranscript).length / 100) || 1) : 1}
            disabled={loading || isListening}
          />

          <div className="flex items-center justify-center gap-2">
            <div className="flex items-center gap-2 md:gap-3 min-w-0">
              <button
                onClick={toggleMic}
                disabled={!hasBrowserSupport}
                className={`relative h-12 rounded-lg border-2 flex items-center justify-center overflow-hidden shadow-sm transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed ${
                  isListening
                    ? "w-30 border-[#2E74C8] bg-[#EEF5FF] text-[#1E4F8D]"
                    : "w-20 border-transparent bg-[#70B147] text-white hover:bg-[#63A03F]"
                }`}
                title={!hasBrowserSupport ? "Trình duyệt không hỗ trợ nhận diện giọng nói" : isListening ? "Dừng ghi âm" : "Bật ghi âm"}
              >
                <span
                  className={`absolute inset-0 flex items-center justify-center transition-all duration-300 ${
                    isListening ? "opacity-0 scale-90" : "opacity-100 scale-100"
                  }`}
                >
                  <AudioLines size={18} className={isListening ? "text-[#1E4F8D]" : "text-white"} />
                  <span className="text-xs font-semibold leading-none ml-2">Nói</span>
                </span>

                <span
                  className={`absolute inset-0 flex items-center justify-center gap-2 transition-all duration-300 ${
                    isListening ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"
                  }`}
                >
                  <span className="flex items-end gap-2 h-3" aria-hidden>
                    <span className="speak-bar" />
                    <span className="speak-bar" />
                    <span className="speak-bar" />
                  </span>
                  <span className="text-xs font-semibold leading-none">Dừng</span>
                </span>
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setVoiceEnabled((v) => !v)}
                title={voiceEnabled ? "Tắt tiếng đọc" : "Bật tiếng đọc"}
                className="h-12 w-12 rounded-lg bg-white/90 flex items-center justify-center shadow-sm hover:bg-white transition-colors"
              >
                {voiceEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>

              <button
                type="button"
                className="h-12 w-12  rounded-lg text-[#45484D] hover:bg-black/5 transition-colors flex items-center justify-center border-[1.5px] border-gray-300 disabled:cursor-not-allowed disabled:opacity-50"
                title="Gửi"
                onClick={handleSendMessage}
              >
                <Send size={20}/>
              </button>
            </div>
          </div>
        </div>

      </main>


      {/* 2. RIGHT SIDEBAR: Live Metrics & Hints (Mostly hidden on mobile, or bottom scroll) */}
  <aside className="hidden lg:flex w-75 xl:w-85 flex-col bg-white rounded-3xl p-4 shadow-sm border border-[#2F4F4F]/5">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 bg-[#F9F9F2] rounded-xl text-[#2F4F4F]">
            <Activity size={24} />
          </div>
          <div>
            <h2 className="font-heading font-bold text-lg leading-tight uppercase tracking-wide">Chỉ số & Gợi ý</h2>
            <p className="text-xs text-[#5A6D6D]">Phân tích trực tiếp AI</p>
          </div>
        </div>

        <div className="space-y-6 flex-1 overflow-y-auto custom-scrollbar pr-2 pb-6">

          {/* Gợi ý từ Đậu */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 mb-1">
              <Lightbulb size={16} className="text-yellow-500" />
              <h3 className="font-heading font-bold text-sm uppercase tracking-wide text-[#2F4F4F]">Gợi ý trả lời</h3>
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 shadow-sm relative">
              <p className="text-sm text-[#2F4F4F] leading-relaxed">
                {latestHint}
              </p>
            </div>
          </div>

          <hr className="border-t border-gray-100" />

          {/* Progress Bar 1 */}
          <div>
            <div className="flex justify-between items-end mb-3">
              <span className="text-sm font-semibold flex items-center gap-2"><Sparkles size={16} className="text-(--primary)"/> Độ tự tin</span>
              <span className="text-lg font-bold font-mono">{liveMetrics.confidence_score}%</span>
            </div>
            <div className="h-3 w-full bg-[#F9F9F2] rounded-full overflow-hidden">
              <div 
                className="h-full bg-linear-to-r from-(--primary) to-[#4A7F4A] rounded-full transition-all duration-500 ease-out" 
                style={{ width: `${liveMetrics.confidence_score}%` }}>
              </div>
            </div>
            <p className="text-xs text-[#5A6D6D] mt-2 italic">{liveMetrics.confidence_feedback}</p>
          </div>

          {/* Progress Bar 2 */}
          <div>
            <div className="flex justify-between items-end mb-3">
              <span className="text-sm font-semibold flex items-center gap-2"><Target size={16} className="text-(--primary)"/> Bám sát JD</span>
              <span className="text-lg font-bold font-mono">{liveMetrics.jd_relevance_score}%</span>
            </div>
            <div className="h-3 w-full bg-[#F9F9F2] rounded-full overflow-hidden">
              <div 
                className="h-full bg-yellow-400 rounded-full transition-all duration-500 ease-out" 
                style={{ width: `${liveMetrics.jd_relevance_score}%` }}>
              </div>
            </div>
            <p className="text-xs text-[#5A6D6D] mt-2 italic">{liveMetrics.jd_relevance_feedback}</p>
          </div>

          {/* Status Metric */}
          <div className="bg-[#E8EFD5]/50 p-4 rounded-2xl border border-(--primary)/20">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center shrink-0">
                <BrainCircuit size={16} className="text-(--primary)"/>
              </div>
              <span className="font-semibold text-sm">Từ vựng chuyên ngành</span>
            </div>
            <p className="text-[#2F4F4F] font-bold text-xl ml-11">
              {liveMetrics.tech_vocab_rating} <Zap size={18} fill="#FFBD2E" color="#FFBD2E" className="inline mb-1"/>
            </p>
          </div>
        </div>

        {/* End Interview Button */}
        <button 
          onClick={endInterview}
          className="mt-4 py-2 w-full rounded-xl border-2 border-red-500/20 text-red-600 font-bold hover:bg-red-50 transition-colors flex items-center justify-center gap-2 shrink-0"
        >
          <PhoneOff size={20} />
          Kết thúc phỏng vấn
        </button>
      </aside>
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(47, 79, 79, 0.1); border-radius: 10px; }
        .custom-scrollbar:hover::-webkit-scrollbar-thumb { background: rgba(47, 79, 79, 0.2); }
        
        @keyframes pulse-wave {
          0% { box-shadow: 0 0 0 0 rgba(178, 34, 34, 0.4); }
          70% { box-shadow: 0 0 0 15px rgba(178, 34, 34, 0); }
          100% { box-shadow: 0 0 0 0 rgba(178, 34, 34, 0); }
        }
        .mic-recording {
          animation: pulse-wave 1.5s infinite;
          background-color: #B22222 !important;
        }
        .mic-idle {
          background-color: var(--primary);
        }

        @keyframes audio-bounce {
          0%, 100% { height: 6px; }
          50% { height: 20px; }
        }
        .audio-bar {
          width: 4px;
          background-color: var(--primary);
          border-radius: 2px;
          animation: audio-bounce 1s ease-in-out infinite;
        }
        .audio-bar:nth-child(2) { animation-delay: 0.2s; }
        .audio-bar:nth-child(3) { animation-delay: 0.4s; }
        .audio-bar:nth-child(4) { animation-delay: 0.1s; }

        @keyframes speak-bounce {
          0%, 100% { height: 6px; }
          50% { height: 16px; }
        }
        .speak-bar {
          width: 3px;
          height: 6px;
          border-radius: 3px;
          background: #1E4F8D;
          animation: speak-bounce 0.9s ease-in-out infinite;
        }
        .speak-bar:nth-child(2) { animation-delay: 0.15s; }
        .speak-bar:nth-child(3) { animation-delay: 0.3s; }
      `}</style>
    </div>
  );
}
