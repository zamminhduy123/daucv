"use client";

// Web Speech API type declarations
declare class SpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}
declare class SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Send, Mic, MicOff, PhoneOff, Target, Sparkles, BrainCircuit, Activity, Zap } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  feedback?: string;
}

// Initial Mock Data to visualize the layout immediately
const MOCK_MESSAGES: Message[] = [
  { 
    role: "assistant", 
    content: "Chào bạn. Cảm ơn bạn đã tham gia buổi phỏng vấn vị trí Frontend Developer hôm nay. Bạn có thể giới thiệu ngắn gọn về thế mạnh lớn nhất của mình được không?" 
  },
  { 
    role: "user", 
    content: "Chào Đậu, thế mạnh của mình làm việc tốt với React và TypeScript. Mình học cũng khá nhanh.", 
    feedback: "💡 Đậu Insight: Trả lời hơi chung chung. Hãy nhắc đến một metrics hoặc dự án cụ thể chứng minh việc 'học nhanh' nhé." 
  },
  { 
    role: "assistant", 
    content: "Nghe rất thú vị! Trong JD có yêu cầu kinh nghiệm tối ưu hóa hiệu suất (Performance Optimization). Bạn có thể chia sẻ một ví dụ thực tế bạn đã áp dụng không?" 
  }
];

export default function InterviewPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>(MOCK_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [lang] = useState<"vi-VN" | "en-US">("vi-VN");
  const bottomRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Scroll to bottom when messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle actual API Call
  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input.trim() };
    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput("");
    setLoading(true);

    try {
      // Simulate network request here since we didn't hook up a persistent ID in mock mode
      setTimeout(() => {
        setMessages(prev => [
           ...prev, 
           { 
             role: "assistant", 
             content: "Tôi hiểu, hướng tiếp cận đó khá tốt. Vậy nếu hệ thống đột ngột gặp lỗi crash liên tục do memory leak, bạn sẽ bắt đầu debug từ đâu?"
           }
        ]);
        setLoading(false);
      }, 1500);
      
    } catch {
      setMessages([...newHistory, { role: "assistant", content: "⚠️ Đậu đang gặp sự cố mạng một chút..." }]);
      setLoading(false);
    }
  };

  const toggleMic = () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (!SR) { alert("Trình duyệt không hỗ trợ nhận diện giọng nói."); return; }
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const rec = new SR();
    rec.lang = lang;
    rec.continuous = false;
    rec.onresult = (e: SpeechRecognitionEvent) => setInput((prev) => prev + " " + e.results[0][0].transcript);
    rec.onend = () => setListening(false);
    rec.start();
    recognitionRef.current = rec;
    setListening(true);
  };

  const endInterview = () => {
    router.push("/results");
  };

  return (
    <div className="min-h-screen w-full bg-[#F9F9F2] text-[#2F4F4F] font-sans p-4 md:p-6 overflow-hidden flex flex-col md:flex-row gap-6">
      
      {/* 1. LEFT SIDEBAR: Job Context (25%) */}
      <aside className="hidden lg:flex flex-col w-1/4 bg-white rounded-3xl p-6 shadow-sm border border-[#2F4F4F]/5 relative">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2.5 bg-[var(--primary)]/20 rounded-xl text-[var(--primary)]">
            <Target size={24} />
          </div>
          <div>
            <h2 className="font-heading font-bold text-lg leading-tight uppercase tracking-wide">Thông tin vị trí</h2>
            <p className="text-xs text-[#5A6D6D]">Dựa trên JD đã nhập</p>
          </div>
        </div>

        <div className="space-y-6 flex-1 overflow-y-auto pr-2 custom-scrollbar">
          <div>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[var(--primary)]"></span>
              Keyword Trọng tâm
            </h3>
            <div className="flex flex-wrap gap-2">
              {["React", "TypeScript", "Performance", "Clean Code"].map(k => (
                <span key={k} className="px-3 py-1.5 bg-[#E8EFD5] text-[#2F4F4F] text-xs font-semibold rounded-lg">
                  {k}
                </span>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[var(--primary)]"></span>
              JD Tóm tắt
            </h3>
            <p className="text-sm leading-relaxed text-[#5A6D6D] bg-[#F9F9F2] p-4 rounded-2xl">
              Xây dựng kiến trúc frontend scale lớn, tối ưu hóa tốc độ tải trang dưới 2s. 
              Review code và duy trì chuẩn mực Clean Code trong team.
            </p>
          </div>
        </div>

        <button 
          onClick={endInterview}
          className="mt-6 w-full py-4 rounded-xl border-2 border-red-500/20 text-red-600 font-bold hover:bg-red-50 transition-colors flex items-center justify-center gap-2"
        >
          <PhoneOff size={20} />
          Kết thúc phỏng vấn
        </button>
      </aside>


      {/* 2. MAIN CENTER AREA: Conversation (50%) */}
      <main className="flex-1 flex flex-col bg-white rounded-3xl shadow-sm border border-[#2F4F4F]/5 relative overflow-hidden h-[calc(100vh-3rem)]">
        
        {/* Header Avatar */}
        <header className="h-28 border-b border-[#2F4F4F]/5 flex items-center justify-center px-8 shrink-0 bg-white z-10 shadow-sm relative">
          <div className="flex flex-col items-center gap-2">
            <div className={`relative ${listening ? 'w-16 h-16' : 'w-14 h-14'} transition-all duration-300 rounded-full bg-[#E8EFD5] shadow-sm flex items-center justify-center`}>
              <Image src="/main-icon.webp" alt="Bé Đậu" width={32} height={32} />
              
              {/* Audio Wave Animation when recording */}
              {listening && (
                <div className="absolute -right-12 flex items-end gap-1 h-8">
                  <div className="audio-bar"></div>
                  <div className="audio-bar"></div>
                  <div className="audio-bar"></div>
                  <div className="audio-bar"></div>
                </div>
              )}
            </div>
            <p className="text-xs font-semibold text-[var(--primary)] uppercase tracking-widest">
              {listening ? "Bé Đậu đang nghe..." : loading ? "Bé Đậu đang nghĩ..." : "Bé Đậu đang nói..."}
            </p>
          </div>
        </header>

        {/* Transcript Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 bg-[#FAFAFA] custom-scrollbar pb-48">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"} max-w-[85%] ${msg.role === "user" ? "ml-auto" : "mr-auto"}`}>
              {/* Chat Bubble */}
              <div 
                className={`p-5 rounded-2xl text-[1.05rem] leading-relaxed shadow-sm
                  ${msg.role === "assistant" 
                    ? "bg-[#E8EFD5] text-[#2F4F4F] rounded-tl-sm border border-[var(--primary)]/20" 
                    : "bg-white text-[#2F4F4F] rounded-tr-sm border border-gray-200"
                  }`}
              >
                {msg.content}
              </div>

              {/* Unique 2026 AI Insight Card for User Messages */}
              {msg.role === "user" && msg.feedback && (
                <div className="mt-3 bg-white border-2 border-[var(--primary)]/20 text-[#2F4F4F] text-sm p-3.5 rounded-xl flex items-start gap-3 shadow-sm mr-2 max-w-sm">
                  <span className="text-xl">💡</span>
                  <p className="leading-snug">{msg.feedback}</p>
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
          <div className="h-40 shrink-0" />
        </div>

        {/* Bottom Floating Console */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[90%] md:w-[85%] bg-white rounded-3xl shadow-xl border border-gray-100 p-4 pb-5 flex flex-col items-center gap-4">
          {/* Giant Mic Button */}
          <button 
            onClick={toggleMic}
            className={`w-20 h-20 rounded-full flex items-center justify-center -mt-12 shadow-lg transition-transform duration-300 hover:scale-105 active:scale-95 ${listingClass(listening)}`} 
          >
            {listening ? <MicOff size={32} color="white" /> : <Mic size={32} color="white" />}
          </button>

          {/* Fallback Text Input */}
          <div className="w-full flex items-center gap-3 bg-[#F9F9F2] rounded-2xl border border-gray-200 px-4 py-2 hover:border-[var(--primary)] transition-colors focus-within:border-[var(--primary)] focus-within:ring-2 focus-within:ring-[var(--primary)]/20">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Hoặc gõ câu trả lời của bạn..."
              className="flex-1 bg-transparent border-none outline-none text-[0.95rem] text-[#2F4F4F] py-2"
              disabled={loading || listening}
            />
            <button 
              onClick={sendMessage}
              disabled={!input.trim() || loading || listening}
              className="w-10 h-10 rounded-xl bg-[#2F4F4F] flex items-center justify-center text-white shrink-0 disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-black transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>

      </main>


      {/* 3. RIGHT SIDEBAR: Live Metrics (25%) */}
      <aside className="hidden xl:flex flex-col w-1/4 bg-white rounded-3xl p-6 shadow-sm border border-[#2F4F4F]/5">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2.5 bg-[#F9F9F2] rounded-xl text-[#2F4F4F]">
            <Activity size={24} />
          </div>
          <div>
            <h2 className="font-heading font-bold text-lg leading-tight uppercase tracking-wide">Chỉ số hiện tại</h2>
            <p className="text-xs text-[#5A6D6D]">Live assessment from AI</p>
          </div>
        </div>

        <div className="space-y-8">
          {/* Progress Bar 1 */}
          <div>
            <div className="flex justify-between items-end mb-3">
              <span className="text-sm font-semibold flex items-center gap-2"><Sparkles size={16} className="text-[var(--primary)]"/> Độ tự tin</span>
              <span className="text-lg font-bold font-mono">80%</span>
            </div>
            <div className="h-3 w-full bg-[#F9F9F2] rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-[var(--primary)] to-[#4A7F4A] rounded-full w-[80%]"></div>
            </div>
            <p className="text-xs text-[#5A6D6D] mt-2 italic">Giọng nói rõ ràng, trôi chảy.</p>
          </div>

          {/* Progress Bar 2 */}
          <div>
            <div className="flex justify-between items-end mb-3">
              <span className="text-sm font-semibold flex items-center gap-2"><Target size={16} className="text-[var(--primary)]"/> Mức độ bám sát JD</span>
              <span className="text-lg font-bold font-mono">65%</span>
            </div>
            <div className="h-3 w-full bg-[#F9F9F2] rounded-full overflow-hidden">
              <div className="h-full bg-yellow-400 rounded-full w-[65%]"></div>
            </div>
            <p className="text-xs text-[#5A6D6D] mt-2 italic">Cần chú trọng hơn vào các kỹ năng cốt lõi.</p>
          </div>

          {/* Status Metric */}
          <div className="bg-[#E8EFD5]/50 p-4 rounded-2xl border border-[var(--primary)]/20">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center shrink-0">
                <BrainCircuit size={16} className="text-[var(--primary)]"/>
              </div>
              <span className="font-semibold text-sm">Từ vựng chuyên ngành</span>
            </div>
            <p className="text-[#2F4F4F] font-bold text-xl ml-11">TỐT <Zap size={18} fill="#FFBD2E" color="#FFBD2E" className="inline mb-1"/></p>
          </div>
        </div>
      </aside>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(47,79,79,0.1); border-radius: 10px; }
        .custom-scrollbar:hover::-webkit-scrollbar-thumb { background: rgba(47,79,79,0.2); }
        
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
      `}</style>
    </div>
  );
}

// Helper for button classes
function listingClass(listening: boolean) {
  return listening ? 'mic-recording' : 'mic-idle hover:bg-[#86b17c]';
}
