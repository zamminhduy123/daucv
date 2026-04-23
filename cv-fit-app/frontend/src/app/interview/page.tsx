"use client";

// Web Speech API type declarations (not included in standard TS lib)
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
import Link from "next/link";
import { Send, Mic, MicOff, Volume2 } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// Buy Me a Coffee modal (Rebranded to Chè Đậu Đỏ)
function CoffeeModal({ onClose }: { onClose: () => void }) {
  return (
    <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(47,79,79,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
      <div className="fade-up" style={{ backgroundColor: "#FFFFFF", borderRadius: 24, padding: "3rem 2.5rem", maxWidth: 440, width: "90%", textAlign: "center", boxShadow: "0 32px 64px rgba(47,79,79,0.25)" }}>
        <div style={{ fontSize: "3.5rem", marginBottom: "1.5rem" }}>🍵</div>
        <h2 className="font-heading" style={{ fontSize: "1.75rem", fontWeight: 700, color: "#2F4F4F", marginBottom: "1rem" }}>Tiếp thêm may mắn cho Đậu?</h2>
        <p style={{ color: "#5A6D6D", lineHeight: 1.7, marginBottom: "2.5rem", fontSize: "1.05rem" }}>
          Bé Đậu đã nỗ lực hết mình để giúp bạn có một CV "nét". 
          Hãy tặng Admin một bát <strong style={{ color: "#B22222" }}>Chè Đậu Đỏ</strong> để giữ lấy may mắn cho vòng phỏng vấn sắp tới nhé!
        </p>
        {/* QR Placeholder */}
        <div style={{ width: 180, height: 180, margin: "0 auto 2.5rem", backgroundColor: "rgba(152,193,142,0.1)", borderRadius: 20, border: "2px dashed #98C18E", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "0.5rem" }}>
          <span style={{ fontSize: "2.5rem" }}>📱</span>
          <span style={{ fontSize: "0.85rem", color: "#5A6D6D", fontWeight: 600 }}>Quét mã VietQR</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <button className="btn-red" style={{ width: "100%", justifyContent: "center" }}>
                Tặng Chè Đậu Đỏ (20k) 🍵
            </button>
            <button
                onClick={onClose}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "0.9rem", color: "#5A6D6D", fontWeight: 500 }}
            >
                Để sau nhé, mình đang gấp
            </button>
        </div>
      </div>
    </div>
  );
}

export default function InterviewPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [lang, setLang] = useState<"vi-VN" | "en-US">("vi-VN");
  const [showCoffee, setShowCoffee] = useState(false);
  const [jdText, setJdText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    const jd = sessionStorage.getItem("cvfit_jd");
    const result = sessionStorage.getItem("cvfit_result");
    if (!jd || !result) { router.push("/app"); return; }
    setJdText(jd);

    // Kick off interview with opening AI message
    const parsed = JSON.parse(result);
    const cvText = JSON.stringify(parsed.tailored_cv);
    startInterview(jd, cvText);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (messages.filter((m) => m.role === "user").length >= 5) {
      setShowCoffee(true);
    }
  }, [messages]);

  const startInterview = async (jd: string, cv: string) => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/interview/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jd_text: jd, cv_text: cv, chat_history: [] }),
      });
      const data = await res.json();
      const aiMsg: Message = { role: "assistant", content: data.response };
      setMessages([aiMsg]);
      speak(data.response);
    } catch {
      setMessages([{ role: "assistant", content: "Xin chào! Mình là Bé Đậu, người đồng hành cùng bạn hôm nay. Rất tiếc là mình chưa kết nối được máy chủ — hãy kiểm tra lại FastAPI nhé!" }]);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input.trim() };
    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput("");
    setLoading(true);

    const result = sessionStorage.getItem("cvfit_result");
    const cvText = result ? JSON.stringify(JSON.parse(result).tailored_cv) : "";

    try {
      const res = await fetch("http://localhost:8000/api/interview/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jd_text: jdText, cv_text: cvText, chat_history: newHistory }),
      });
      const data = await res.json();
      const aiMsg: Message = { role: "assistant", content: data.response };
      setMessages([...newHistory, aiMsg]);
      speak(data.response);
    } catch {
      setMessages([...newHistory, { role: "assistant", content: "⚠️ Đậu đang bị nghẽn mạng một chút..." }]);
    } finally {
      setLoading(false);
    }
  };

  const speak = (text: string) => {
    if (!window.speechSynthesis) return;
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    u.rate = 1.0;
    window.speechSynthesis.speak(u);
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

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F9F9F2", display: "flex", flexDirection: "column" }}>
      {showCoffee && <CoffeeModal onClose={() => setShowCoffee(false)} />}
      
      {/* NAV */}
      <header style={{ padding: "1rem 2rem", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(47,79,79,0.08)", backgroundColor: "white" }}>
        <Link href="/" className="font-heading" style={{ fontSize: "1.5rem", fontWeight: 700, textDecoration: "none", color: "#2F4F4F", display: "flex", alignItems: "center", gap: "0.5rem" }}>🌱 Đậu</Link>
        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
          {/* Language toggle */}
          <button
            onClick={() => setLang(lang === "en-US" ? "vi-VN" : "en-US")}
            style={{ padding: "0.5rem 1.25rem", borderRadius: 12, border: "1px solid #98C18E", backgroundColor: "rgba(152,193,142,0.1)", color: "#2F4F4F", fontSize: "0.85rem", fontWeight: 600, cursor: "pointer", transition: "all 0.2s" }}
          >
            {lang === "en-US" ? "🇺🇸 English" : "🇻🇳 Tiếng Việt"}
          </button>
          <Link href="/results" style={{ fontSize: "0.9rem", color: "#5A6D6D", textDecoration: "none", fontWeight: 500 }}>← Kết quả</Link>
        </div>
      </header>

      {/* CHAT WINDOW */}
      <div style={{ flex: 1, maxWidth: 800, width: "100%", margin: "0 auto", padding: "2rem 1.5rem", overflowY: "auto", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {messages.length === 0 && !loading && (
          <div style={{ textAlign: "center", paddingTop: "5rem", color: "#5A6D6D" }}>
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🌱</div>
            <p className="font-heading" style={{ fontWeight: 600, fontSize: "1.1rem" }}>Bé Đậu đang chuẩn bị câu hỏi...</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start", alignItems: "flex-end", gap: "0.75rem" }}>
            {msg.role === "assistant" && (
              <div style={{ width: 36, height: 36, borderRadius: 12, backgroundColor: "#98C18E", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: "0 4px 12px rgba(152,193,142,0.2)" }}>
                <span style={{ fontSize: "1.2rem" }}>🌱</span>
              </div>
            )}
            <div
              style={{
                maxWidth: "75%",
                padding: "1rem 1.25rem",
                borderRadius: msg.role === "user" ? "20px 20px 4px 20px" : "20px 20px 20px 4px",
                backgroundColor: msg.role === "user" ? "#2F4F4F" : "white",
                color: msg.role === "user" ? "white" : "#2F4F4F",
                fontSize: "1rem",
                lineHeight: 1.6,
                boxShadow: msg.role === "assistant" ? "0 4px 12px rgba(0,0,0,0.03)" : "0 4px 12px rgba(47,79,79,0.1)",
                border: msg.role === "assistant" ? "1px solid rgba(0,0,0,0.03)" : "none",
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem" }}>
            <div style={{ width: 36, height: 36, borderRadius: 12, backgroundColor: "#98C18E", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ fontSize: "1.2rem" }}>🌱</span>
            </div>
            <div style={{ backgroundColor: "white", padding: "1rem 1.5rem", borderRadius: "20px 20px 20px 4px", border: "1px solid rgba(0,0,0,0.03)", boxShadow: "0 4px 12px rgba(0,0,0,0.03)" }}>
              <span style={{ display: "flex", gap: "6px" }}>
                {[0, 0.15, 0.3].map((d) => (
                  <span key={d} style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#98C18E", display: "inline-block", animation: `bounce 0.8s ${d}s ease-in-out infinite` }} />
                ))}
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* INPUT BAR */}
      <div style={{ borderTop: "1px solid rgba(47,79,79,0.08)", backgroundColor: "white", padding: "1.5rem" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", display: "flex", gap: "1rem", alignItems: "flex-end" }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Chia sẻ suy nghĩ của bạn với Bé Đậu..."
            rows={2}
            style={{ flex: 1, padding: "1rem 1.25rem", borderRadius: 16, border: "1px solid rgba(47,79,79,0.12)", fontSize: "1rem", lineHeight: 1.5, fontFamily: "'Inter',sans-serif", resize: "none", outline: "none", transition: "border-color 0.2s" }}
            onFocus={(e) => e.target.style.borderColor = "#98C18E"}
            onBlur={(e) => e.target.style.borderColor = "rgba(47,79,79,0.12)"}
          />
          <button
            onClick={toggleMic}
            style={{ width: 52, height: 52, borderRadius: 16, border: "1px solid rgba(47,79,79,0.1)", backgroundColor: listening ? "#B22222" : "#F9F9F2", color: listening ? "white" : "#2F4F4F", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "all 0.2s" }}
          >
            {listening ? <MicOff size={22} /> : <Mic size={22} />}
          </button>
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            style={{ width: 52, height: 52, borderRadius: 16, backgroundColor: input.trim() && !loading ? "#98C18E" : "#E8EFD5", color: "white", border: "none", display: "flex", alignItems: "center", justifyContent: "center", cursor: input.trim() && !loading ? "pointer" : "not-allowed", transition: "all 0.2s", boxShadow: input.trim() && !loading ? "0 4px 12px rgba(152,193,142,0.3)" : "none" }}
          >
            <Send size={22} />
          </button>
        </div>
      </div>


      {showCoffee && <CoffeeModal onClose={() => setShowCoffee(false)} />}

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
      `}</style>
    </div>
  );
}
