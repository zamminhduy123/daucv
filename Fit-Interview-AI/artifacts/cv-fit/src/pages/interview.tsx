import { useEffect, useState, useRef } from "react";
import { useLocation } from "wouter";
import { useInterviewChat, type ChatMessage } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ArrowLeft, Send, Mic, X, Coffee } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

// Web Speech API interfaces
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}
interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}
interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: (this: SpeechRecognition, ev: SpeechRecognitionEvent) => any;
  onerror: (this: SpeechRecognition, ev: any) => any;
  onend: (this: SpeechRecognition, ev: Event) => any;
}
declare var SpeechRecognition: { prototype: SpeechRecognition; new(): SpeechRecognition };
declare var webkitSpeechRecognition: { prototype: SpeechRecognition; new(): SpeechRecognition };

export default function Interview() {
  const [location, setLocation] = useLocation();
  const [jdText, setJdText] = useState("");
  const [cvText, setCvText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [lang, setLang] = useState<"vi-VN" | "en-US">("vi-VN");
  const [showCoffeeModal, setShowCoffeeModal] = useState(false);
  const [aiMessageCount, setAiMessageCount] = useState(0);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const interviewChat = useInterviewChat();
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    const jd = sessionStorage.getItem("jd_text");
    const cv = sessionStorage.getItem("cv_text");
    if (!jd || !cv) {
      setLocation("/app");
      return;
    }
    setJdText(jd);
    setCvText(cv);

    // Initial greeting if empty
    if (messages.length === 0) {
      setMessages([{
        role: "assistant",
        content: "Hello! I'm your AI interviewer. Let's get started. Could you briefly introduce yourself based on your CV?"
      }]);
    }
  }, [setLocation, messages.length]);

  useEffect(() => {
    // Scroll to bottom on new message
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Check coffee modal condition
  useEffect(() => {
    if (aiMessageCount >= 5 && !showCoffeeModal) {
      // Show once per session
      const hasShown = sessionStorage.getItem("coffeeModalShown");
      if (!hasShown) {
        setShowCoffeeModal(true);
        sessionStorage.setItem("coffeeModalShown", "true");
      }
    }
  }, [aiMessageCount, showCoffeeModal]);

  // Setup Web Speech API
  useEffect(() => {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRec) {
      const recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.interimResults = false;
      
      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInputValue((prev) => prev ? prev + " " + transcript : transcript);
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in your browser.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.lang = lang;
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const handleSend = () => {
    if (!inputValue.trim()) return;

    const userMessage: ChatMessage = { role: "user", content: inputValue.trim() };
    const newHistory = [...messages, userMessage];
    setMessages(newHistory);
    setInputValue("");

    interviewChat.mutate({
      data: {
        jd_text: jdText,
        cv_text: cvText,
        chat_history: newHistory
      }
    }, {
      onSuccess: (res) => {
        setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
        setAiMessageCount(c => c + 1);
      }
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setLocation("/results")} className="text-slate-500 hover:text-slate-900 rounded-full">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3">
            <Avatar className="w-10 h-10 border border-slate-200">
              <AvatarFallback className="bg-emerald-100 text-emerald-700 font-bold">AI</AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-sm font-bold text-slate-900">HR Consultant</h2>
              <p className="text-xs text-emerald-600 font-medium">Mock Interview Session</p>
            </div>
          </div>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => setLang(lang === "vi-VN" ? "en-US" : "vi-VN")}
          className="text-xs font-medium border-slate-300"
        >
          {lang === "vi-VN" ? "🇻🇳 VI" : "🇺🇸 EN"}
        </Button>
      </header>

      {/* Chat Area */}
      <main 
        className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6"
        ref={chatContainerRef}
      >
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map((msg, idx) => {
            const isUser = msg.role === "user";
            return (
              <div key={idx} className={`flex ${isUser ? "justify-end" : "justify-start"} items-end gap-2`}>
                {!isUser && (
                  <Avatar className="w-8 h-8 shrink-0 mb-1 border border-slate-200">
                    <AvatarFallback className="bg-emerald-100 text-emerald-700 text-xs font-bold">AI</AvatarFallback>
                  </Avatar>
                )}
                
                <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-3 ${
                  isUser 
                    ? "bg-slate-900 text-white rounded-br-none" 
                    : "bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-sm"
                }`}>
                  <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">{msg.content}</p>
                </div>
              </div>
            );
          })}

          {interviewChat.isPending && (
            <div className="flex justify-start items-end gap-2">
              <Avatar className="w-8 h-8 shrink-0 mb-1 border border-slate-200">
                <AvatarFallback className="bg-emerald-100 text-emerald-700 text-xs font-bold">AI</AvatarFallback>
              </Avatar>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-none px-5 py-4 shadow-sm flex space-x-1.5">
                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t border-slate-200 p-4 shrink-0">
        <div className="max-w-3xl mx-auto relative flex items-center">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleListening}
            className={`absolute left-2 shrink-0 rounded-full transition-colors z-10 ${
              isListening ? "bg-red-100 text-red-600 hover:bg-red-200" : "text-slate-400 hover:text-slate-600"
            }`}
          >
            <Mic className="w-5 h-5" />
          </Button>
          
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? "Listening..." : "Type your answer..."}
            className="pl-14 pr-14 py-6 text-base rounded-full border-slate-300 focus-visible:ring-emerald-500 bg-slate-50"
            disabled={interviewChat.isPending}
          />
          
          <Button
            size="icon"
            onClick={handleSend}
            disabled={!inputValue.trim() || interviewChat.isPending}
            className="absolute right-2 shrink-0 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white z-10"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <div className="text-center mt-2">
          <span className="text-[10px] text-slate-400">Current STT language: {lang === "vi-VN" ? "Vietnamese" : "English"}</span>
        </div>
      </footer>

      {/* Buy me a Coffee Modal */}
      <Dialog open={showCoffeeModal} onOpenChange={setShowCoffeeModal}>
        <DialogContent className="sm:max-w-md bg-white border-slate-200 rounded-2xl">
          <DialogHeader>
            <div className="mx-auto w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mb-4">
              <Coffee className="w-6 h-6 text-amber-600" />
            </div>
            <DialogTitle className="text-center text-xl">Buy Me a Coffee</DialogTitle>
            <DialogDescription className="text-center text-base pt-2 text-slate-600">
              Did this help you prepare? Buy me a Phin coffee to keep the servers running! ☕
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-6">
            {/* QR Placeholder */}
            <div className="w-48 h-48 bg-slate-100 rounded-xl flex items-center justify-center border-2 border-slate-200 overflow-hidden">
               <div className="grid grid-cols-5 grid-rows-5 gap-1 w-32 h-32 opacity-20">
                 {Array.from({length: 25}).map((_, i) => (
                   <div key={i} className="bg-slate-900 rounded-sm"></div>
                 ))}
               </div>
               <div className="absolute font-mono font-bold text-slate-400 rotate-45 text-xl tracking-widest">VIETQR</div>
            </div>
            <p className="mt-4 text-sm font-medium text-slate-500">Scan with Momo or any banking app</p>
          </div>
          <div className="flex justify-center mt-2">
            <Button variant="outline" onClick={() => setShowCoffeeModal(false)} className="rounded-full px-8">
              Maybe Later
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
