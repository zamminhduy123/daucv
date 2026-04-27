import { useState } from "react";
import { sendInterviewChatAPI } from "@/lib/api";

export interface Message {
  role: "user" | "assistant";
  content: string;
  feedback?: string;
  hint_for_user?: string;
}

export interface LiveMetrics {
  confidence_score: number;
  confidence_feedback: string;
  jd_relevance_score: number;
  jd_relevance_feedback: string;
  tech_vocab_rating: "YẾU" | "KHÁ" | "TỐT" | "XUẤT SẮC";
}

const INITIAL_METRICS: LiveMetrics = {
  confidence_score: 100,
  confidence_feedback: "Sẵn sàng phỏng vấn.",
  jd_relevance_score: 100,
  jd_relevance_feedback: "Đang phân tích...",
  tech_vocab_rating: "TỐT"
};

export function useInterviewApi(initialMessages: Message[], initialMetrics?: LiveMetrics) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [loading, setLoading] = useState(false);
  const [liveMetrics, setLiveMetrics] = useState<LiveMetrics>(initialMetrics || INITIAL_METRICS);

  const sendMessage = async (userText: string, jdText: string = "", cvText: string = "") => {
    if (!userText.trim() || loading) return;

    // Optimistically add user message
    const userMsg: Message = { role: "user", content: userText.trim() };
    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setLoading(true);

    try {
      // In production, jdText and cvText would be passed from global state or context
      const proxyJdText = jdText || "";
      const proxyCvText = cvText || "";

      const data = await sendInterviewChatAPI(
        proxyJdText,
        proxyCvText,
        newHistory.map(m => ({ role: m.role, content: m.content }))
      );
      
      // We take the AI's feedback on the user's message and attach it to the history
      const updatedHistory = [...newHistory];
      updatedHistory[updatedHistory.length - 1].feedback = data.ai_feedback;

      // Append the AI's next question
      updatedHistory.push({
        role: "assistant",
        content: data.next_question,
        hint_for_user: data.hint_for_user
      });

      setMessages(updatedHistory);
      setLiveMetrics(data.metrics);
    } catch (error) {
      console.error(error);
      setMessages([...newHistory, { role: "assistant", content: "⚠️ Đậu đang gặp sự cố một chút, hãy thử lại nhé..." }]);
    } finally {
      setLoading(false);
    }
  };

  return {
    messages,
    loading,
    liveMetrics,
    sendMessage
  };
}