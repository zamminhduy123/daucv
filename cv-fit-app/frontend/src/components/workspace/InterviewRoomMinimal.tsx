"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { Loader2, Mic, Volume2, VolumeX } from "lucide-react";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { LiveMetrics, Message, useInterviewApi } from "@/hooks/useInterviewApi";
import { useWorkspace } from "@/context/WorkspaceContext";
import { finishInterviewAPI, generateTTSAPI } from "@/lib/api";
import InterviewReport, { FinalInterviewReport } from "./InterviewReport";
import LoadingOverlay from "./LoadingOverlay";

const OPENING_QUESTION =
  "Anh/chị có thể giới thiệu ngắn gọn về bản thân, tập trung vào hành trình từ khi học đại học đến hiện tại, và lý do nào khiến anh/chị chọn theo đuổi lĩnh vực Machine Learning / AI?";

export interface InterviewState {
  messages?: Message[];
  next_question?: string;
  hint_for_user?: string;
  metrics?: LiveMetrics;
  liveMetrics?: LiveMetrics;
  currentQuestion?: number;
  report?: FinalInterviewReport | null;
}

interface InterviewRoomMinimalProps {
  cvText: string;
  jdText: string;
  initialState: InterviewState | null;
  totalQuestions: number;
  interviewType: string;
  onBack: () => void;
}

type AnswerMode = "ready" | "recording" | "typing" | "review";

const IDLE_VOICE_LEVELS = [0, 0, 0, 0];
const VOICE_NOISE_GATE = 0.025;

type WindowWithWebkitAudio = Window &
  typeof globalThis & {
    webkitAudioContext?: typeof AudioContext;
  };

function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function VoiceLevelDots({ levels, active }: { levels: number[]; active: boolean }) {
  return (
    <div className="flex h-7 items-center justify-center gap-1.5" aria-hidden>
      {levels.map((level, index) => (
        <span
          key={index}
          className="h-2.5 w-2.5 rounded-full bg-[#5A9E40] transition-all duration-500 ease-out"
          style={{
            opacity: active ? 0.34 + level * 0.46 : 0.3,
            transform: active
              ? `translateY(${-(level * 16)}px) scale(${0.86 + level * 0.34})`
              : undefined,
          }}
        />
      ))}
    </div>
  );
}

function AiVoiceOrb({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-full border border-[#2F4F4F]/8 bg-white px-3 py-2 shadow-[0_8px_24px_rgba(47,79,79,0.04)]">
      <div className="relative h-8 w-8" aria-hidden>
        <span className="absolute left-1 top-1 h-5 w-5 animate-pulse rounded-full bg-[#5A9E40]/70 blur-[1px]" />
        <span className="absolute right-0 top-1.5 h-4 w-4 animate-pulse rounded-full bg-[#A8C99A]/85 [animation-delay:120ms]" />
        <span className="absolute bottom-0 left-2 h-5 w-5 animate-pulse rounded-full bg-[#EAF4E6] [animation-delay:240ms]" />
        <span className="absolute inset-1 rounded-full border border-[#5A9E40]/20 animate-ping" />
      </div>
      <span className="text-xs font-semibold text-[#5A6D6D]">{label}</span>
    </div>
  );
}

export default function InterviewRoomMinimal({
  cvText,
  jdText,
  initialState,
  totalQuestions,
  interviewType,
  onBack,
}: InterviewRoomMinimalProps) {
  const { setCachedInterview } = useWorkspace();
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [answerMode, setAnswerMode] = useState<AnswerMode>("ready");
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [typedAnswer, setTypedAnswer] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState(initialState?.currentQuestion ?? 1);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [report, setReport] = useState<FinalInterviewReport | null>(initialState?.report ?? null);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isTTSLoading, setIsTTSLoading] = useState(false);
  const [voiceLevels, setVoiceLevels] = useState<number[]>(IDLE_VOICE_LEVELS);
  const textFallbackRef = useRef<HTMLTextAreaElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const audioBlobCacheRef = useRef<Map<string, Blob>>(new Map());
  const audioRequestCacheRef = useRef<Map<string, Promise<Blob>>>(new Map());
  const lastSpokenQuestionRef = useRef<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const meterFrameRef = useRef<number | null>(null);

  const isResuming = Boolean(initialState?.messages);
  const initialMessages: Message[] = isResuming
    ? initialState?.messages ?? []
    : initialState?.next_question
      ? [{ role: "assistant", content: initialState.next_question, hint_for_user: initialState.hint_for_user }]
      : [{ role: "assistant", content: OPENING_QUESTION }];

  const { messages, loading, liveMetrics, sendMessage, setMessages } = useInterviewApi(
    initialMessages,
    isResuming ? initialState?.liveMetrics : initialState?.metrics
  );

  const {
    isListening,
    transcript,
    setTranscript,
    interimTranscript,
    hasBrowserSupport,
    startListening,
    stopListening,
  } = useSpeechRecognition();

  const displayQuestion = useMemo(() => {
    if (currentQuestion === 1) return OPENING_QUESTION;
    const latestAssistant = [...messages].reverse().find((message) => message.role === "assistant");
    return latestAssistant?.content ?? OPENING_QUESTION;
  }, [currentQuestion, messages]);

  const spokenAnswer = [transcript, interimTranscript].filter(Boolean).join(" ").trim();
  const answerText = answerMode === "typing"
    ? typedAnswer.trim()
    : spokenAnswer;
  const shouldShowAiOrb = isTTSLoading || isSpeaking || loading;

  const stopVoiceMeter = useCallback(() => {
    if (meterFrameRef.current) {
      cancelAnimationFrame(meterFrameRef.current);
      meterFrameRef.current = null;
    }

    micStreamRef.current?.getTracks().forEach((track) => track.stop());
    micStreamRef.current = null;

    audioContextRef.current?.close().catch(() => undefined);
    audioContextRef.current = null;
    setVoiceLevels(IDLE_VOICE_LEVELS);
  }, []);

  const startVoiceMeter = useCallback(async () => {
    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) return;

    try {
      stopVoiceMeter();

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioContextConstructor = window.AudioContext || (window as WindowWithWebkitAudio).webkitAudioContext;
      if (!AudioContextConstructor) return;

      const audioContext = new AudioContextConstructor();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);

      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.45;
      const timeDomainData = new Uint8Array(analyser.fftSize);
      source.connect(analyser);
      micStreamRef.current = stream;
      audioContextRef.current = audioContext;

      const updateLevels = () => {
        analyser.getByteTimeDomainData(timeDomainData);

        const chunkSize = Math.floor(timeDomainData.length / 4);
        const nextLevels = [0, 1, 2, 3].map((index) => {
          const start = index * chunkSize;
          const end = index === 3 ? timeDomainData.length : start + chunkSize;
          let sumSquares = 0;

          for (let i = start; i < end; i += 1) {
            const centered = (timeDomainData[i] - 128) / 128;
            sumSquares += centered * centered;
          }

          const rms = Math.sqrt(sumSquares / Math.max(1, end - start));
          const gatedLevel = Math.max(0, rms - VOICE_NOISE_GATE);
          return Math.min(1, gatedLevel * 16);
        });

        setVoiceLevels(nextLevels);
        meterFrameRef.current = requestAnimationFrame(updateLevels);
      };

      updateLevels();
    } catch (error) {
      console.error("Voice meter error:", error);
      setVoiceLevels(IDLE_VOICE_LEVELS);
    }
  }, [stopVoiceMeter]);

  const cleanupAudioUrl = useCallback(() => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  const stopQuestionAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    cleanupAudioUrl();
    setIsSpeaking(false);
  }, [cleanupAudioUrl]);

  const getQuestionAudioBlob = useCallback((text: string) => {
    const cacheKey = text.trim().replace(/\s+/g, " ");
    const cachedBlob = audioBlobCacheRef.current.get(cacheKey);
    if (cachedBlob) return Promise.resolve(cachedBlob);

    const pendingRequest = audioRequestCacheRef.current.get(cacheKey);
    if (pendingRequest) return pendingRequest;

    const request = generateTTSAPI(cacheKey)
      .then((blob) => {
        audioBlobCacheRef.current.set(cacheKey, blob);
        return blob;
      })
      .finally(() => {
        audioRequestCacheRef.current.delete(cacheKey);
      });

    audioRequestCacheRef.current.set(cacheKey, request);
    return request;
  }, []);

  const speakQuestion = useCallback(async (text: string) => {
    if (typeof window === "undefined" || !voiceEnabled) return;

    const cleanText = text.trim().replace(/\s+/g, " ");
    if (!cleanText) return;

    try {
      stopQuestionAudio();
      setIsTTSLoading(!audioBlobCacheRef.current.has(cleanText));

      const blob = await getQuestionAudioBlob(cleanText);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      audioRef.current = audio;
      audioUrlRef.current = url;
      audio.onended = () => {
        cleanupAudioUrl();
        setIsSpeaking(false);
      };

      setIsTTSLoading(false);
      setIsSpeaking(true);
      await audio.play();
    } catch (error) {
      console.error("TTS playback error:", error);
      setIsTTSLoading(false);
      setIsSpeaking(false);
      cleanupAudioUrl();
    }
  }, [cleanupAudioUrl, getQuestionAudioBlob, stopQuestionAudio, voiceEnabled]);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (answerMode !== "recording" || !isListening) return;
    const timer = window.setInterval(() => setRecordingSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, [answerMode, isListening]);

  useEffect(() => {
    return () => stopVoiceMeter();
  }, [stopVoiceMeter]);

  useEffect(() => {
    if (!voiceEnabled || lastSpokenQuestionRef.current === displayQuestion) return;
    lastSpokenQuestionRef.current = displayQuestion;
    speakQuestion(displayQuestion);
  }, [displayQuestion, speakQuestion, voiceEnabled]);

  useEffect(() => {
    const blobCache = audioBlobCacheRef.current;
    const requestCache = audioRequestCacheRef.current;

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      cleanupAudioUrl();
      blobCache.clear();
      requestCache.clear();
    };
  }, [cleanupAudioUrl]);

  useEffect(() => {
    if (messages.length > 0) {
      setCachedInterview({
        ...initialState,
        messages,
        currentQuestion,
        liveMetrics,
        report,
      });
    }
  }, [currentQuestion, initialState, liveMetrics, messages, report, setCachedInterview]);

  useEffect(() => {
    if (answerMode === "typing") textFallbackRef.current?.focus();
  }, [answerMode]);

  const startRecording = () => {
    if (!hasBrowserSupport) {
      alert("Trình duyệt không hỗ trợ nhận diện giọng nói.");
      return;
    }

    setTypedAnswer("");
    setTranscript("");
    setRecordingSeconds(0);
    stopQuestionAudio();
    setAnswerMode("recording");
    startListening();
    startVoiceMeter();
  };

  const toggleRecordingPause = () => {
    if (isListening) {
      stopListening();
      stopVoiceMeter();
      return;
    }
    startListening();
    startVoiceMeter();
  };

  const finishRecording = () => {
    if (isListening) stopListening();
    stopVoiceMeter();
    setAnswerMode("review");
  };

  const cancelRecording = () => {
    if (isListening) stopListening();
    stopVoiceMeter();
    setTranscript("");
    setRecordingSeconds(0);
    setAnswerMode("ready");
  };

  const switchToTyping = () => {
    if (isListening) stopListening();
    stopVoiceMeter();
    stopQuestionAudio();
    setTypedAnswer("");
    setAnswerMode("typing");
  };

  const switchToReady = () => {
    setTypedAnswer("");
    setAnswerMode("ready");
  };

  const toggleVoicePlayback = () => {
    if (voiceEnabled) {
      stopQuestionAudio();
      setVoiceEnabled(false);
      return;
    }

    setVoiceEnabled(true);
    lastSpokenQuestionRef.current = null;
  };

  const retakeRecording = () => {
    setTranscript("");
    setTypedAnswer("");
    setRecordingSeconds(0);
    setAnswerMode("recording");
    startListening();
    startVoiceMeter();
  };

  const editSpokenAnswer = () => {
    setTypedAnswer(spokenAnswer);
    setAnswerMode("typing");
  };

  const submitAnswer = async (answerOverride?: string) => {
    const textToSend = (answerOverride ?? answerText).trim();
    if (!textToSend || loading || isGeneratingReport) return;

    setTranscript("");
    setTypedAnswer("");
    setRecordingSeconds(0);
    setAnswerMode("ready");
    if (isListening) stopListening();
    stopVoiceMeter();

    if (currentQuestion >= totalQuestions) {
      setIsGeneratingReport(true);
      const finalMessage: Message = { role: "user", content: textToSend };
      const fullHistory = [...messages, finalMessage];
      setMessages(fullHistory);

      try {
        const data = await finishInterviewAPI(
          jdText,
          cvText,
          fullHistory.map((message) => ({ role: message.role, content: message.content })),
          interviewType
        );
        setReport(data);
      } catch (error) {
        console.error(error);
        alert("Lỗi khi tạo báo cáo kết quả. Vui lòng thử lại!");
      } finally {
        setIsGeneratingReport(false);
      }
      return;
    }

    const nextQuestion = currentQuestion + 1;
    sendMessage(textToSend, jdText, cvText, nextQuestion, totalQuestions, interviewType);
    setCurrentQuestion(nextQuestion);
  };

  if (report) {
    return (
      <InterviewReport
        report={report}
        interviewType={interviewType}
        onRetry={onBack}
        onHome={onBack}
      />
    );
  }

  return (
    <div className="min-h-[calc(100vh-88px)] text-[#2F4F4F]">
      {isGeneratingReport && (
        <LoadingOverlay
          messages={[
            "Đang tổng hợp kết quả...",
            "Phân tích câu trả lời...",
            "Chuẩn bị báo cáo phỏng vấn...",
          ]}
        />
      )}

      <div className="mx-auto flex h-[calc(100vh-88px)] min-h-170 max-w-370 flex-col">
        <header className="grid h-14 shrink-0 grid-cols-[1fr_auto_1fr] items-center rounded-3xl border border-[#2F4F4F]/8 bg-white/85 px-5 shadow-[0_8px_24px_rgba(47,79,79,0.04)] backdrop-blur">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-2xl bg-[#EEF6EA]">
              <Image src="/main-icon.webp" alt="Bé Đậu" width={20} height={20} style={{ width: "auto", height: "auto" }} className="drop-shadow-sm" />
            </div>
            <span className="font-heading text-[17px] font-bold tracking-tight">Phỏng vấn AI</span>
          </div>

          <div className="text-sm font-semibold text-[#425A5A]">
            Câu hỏi {currentQuestion} / {totalQuestions}
          </div>

          <div className="flex items-center justify-end gap-4">
            <span className="font-mono text-sm font-medium text-[#647373]">{formatDuration(elapsedSeconds)}</span>
            <button
              type="button"
              onClick={onBack}
              className="h-9 rounded-2xl border border-[#2F4F4F]/10 bg-white px-4 text-sm font-semibold text-[#647373] transition-colors hover:border-[#2F4F4F]/20 hover:bg-[#F8FAF5]"
            >
              Thoát
            </button>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,7fr)_minmax(300px,3fr)] gap-5 pt-2">
          <main className="flex min-h-0 flex-col overflow-hidden rounded-[28px] border border-[#2F4F4F]/8 bg-white shadow-[0_14px_40px_rgba(47,79,79,0.045)]">
            <div className="mx-auto flex h-full min-h-0 w-full max-w-[900px] flex-col px-6 py-4">
              <div className="flex w-full max-w-[820px] items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-[#6B7A7A]">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#EEF6EA]">
                    <Image src="/main-icon.webp" alt="Bé Đậu" width={14} height={14} style={{ width: "auto", height: "auto" }} />
                  </span>
                  <span>Bé Đậu · Mở đầu</span>
                </div>

                <div className="flex items-center gap-2">
                  {shouldShowAiOrb && (
                    <AiVoiceOrb
                      label={loading ? "Bé Đậu đang nghĩ" : isTTSLoading ? "Đang chuẩn bị giọng đọc" : "Bé Đậu đang đọc"}
                    />
                  )}
                  {voiceEnabled && (
                    <button
                      type="button"
                      onClick={() => speakQuestion(displayQuestion)}
                      disabled={isTTSLoading}
                      className="inline-flex h-8 items-center gap-1.5 rounded-2xl border border-[#2F4F4F]/8 bg-white px-3 text-xs font-semibold text-[#5A6D6D] transition-colors hover:bg-[#F8FAF5] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isTTSLoading ? <Loader2 size={13} className="animate-spin" /> : <Volume2 size={13} />}
                      Nghe lại
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={toggleVoicePlayback}
                    className="flex h-8 w-8 items-center justify-center rounded-full border border-[#2F4F4F]/8 bg-white text-[#5A6D6D] transition-colors hover:bg-[#F8FAF5]"
                    title={voiceEnabled ? "Tắt giọng đọc" : "Bật giọng đọc"}
                    aria-label={voiceEnabled ? "Tắt giọng đọc" : "Bật giọng đọc"}
                  >
                    {voiceEnabled ? <VolumeX size={14} /> : <Volume2 size={14} />}
                  </button>
                </div>
              </div>

              <section
                className={`mt-4 w-full max-w-205 shrink-0 rounded-3xl border border-[#2F4F4F]/8 bg-[#FBFCF8] transition-all duration-300 ${
                  answerMode === "ready"
                    ? "px-7 py-6"
                    : answerMode === "recording"
                      ? "max-h-[150px] overflow-y-auto px-6 py-4 custom-scrollbar"
                      : "max-h-[220px] overflow-y-auto px-6 py-5 custom-scrollbar"
                }`}
              >
                <p
                  className={`font-semibold leading-[1.48] tracking-normal text-[#263F3F] transition-all duration-300 text-base`}
                >
                  {displayQuestion}
                </p>
              </section>

              <div className="flex min-h-0 flex-1 flex-col justify-start pt-8 xl:pt-10">
                {answerMode === "ready" && (
                  <div className="flex min-h-0 flex-1 flex-col items-center justify-center pb-6 text-center animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <button
                      type="button"
                      onClick={startRecording}
                      disabled={loading || isGeneratingReport}
                      className="group flex h-28 w-28 items-center justify-center rounded-full bg-[var(--primary)] shadow-[0_0_0_8px_rgba(90,158,64,0.055),0_18px_42px_rgba(47,79,79,0.12)] transition-all duration-300 hover:bg-[#4F9339] disabled:cursor-not-allowed disabled:opacity-60 xl:h-[120px] xl:w-[120px]"
                      aria-label="Nhấn để trả lời"
                    >
                      {loading ? (
                        <Loader2 size={34} className="animate-spin text-white" />
                      ) : (
                        <Mic size={36} className="text-white transition-transform duration-300 group-hover:scale-105" />
                      )}
                    </button>

                    <p className="mt-6 text-lg font-bold text-[#2F4F4F]">
                      {isListening ? "Đang nghe..." : loading ? "Đang chuẩn bị câu tiếp theo..." : "Nhấn để trả lời"}
                    </p>
                    <p className="mt-1.5 text-sm font-medium text-[#6B7A7A]">Ưu tiên trả lời bằng giọng nói</p>

                    <button
                      type="button"
                      onClick={switchToTyping}
                      className="mt-4 text-sm font-semibold text-[#5A9E40] underline-offset-4 hover:underline"
                    >
                      Không tiện nói? Gõ thay thế
                    </button>
                  </div>
                )}

                {answerMode === "recording" && (
                  <div className="flex min-h-0 w-full max-w-205 flex-1 flex-col items-center animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div className="mb-5 flex shrink-0 items-center gap-2 rounded-full border border-[#2F4F4F]/8 bg-white px-4 py-2 shadow-[0_8px_24px_rgba(47,79,79,0.04)]">
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          isListening
                            ? "bg-[#5A9E40] shadow-[0_0_0_5px_rgba(90,158,64,0.10)] animate-pulse"
                            : "bg-[#AAB4B4]"
                        }`}
                      />
                      <span className="text-sm font-bold text-[#4F9339]">
                        {isListening ? "Đang lắng nghe" : "Đã tạm dừng"}
                      </span>
                      <span className="text-[#AAB4B4]">·</span>
                      <span className="font-mono text-sm font-semibold text-[#647373]">
                        {formatDuration(recordingSeconds)}
                      </span>
                    </div>

                    <section className="flex min-h-0 w-full flex-1 flex-col rounded-[28px] border border-[#2F4F4F]/10 bg-linear-to-b from-[#FBFCF8] to-white p-6 shadow-[0_10px_28px_rgba(47,79,79,0.035)]">
                      <div className="flex shrink-0 items-center justify-between gap-4">
                        <h3 className="text-sm font-bold text-[#2F4F4F]">Câu trả lời của bạn</h3>
                        <div className="flex items-center gap-3">
                          <VoiceLevelDots levels={voiceLevels} active={isListening} />
                          <p className="text-xs font-semibold text-[#8A9696]">Transcript trực tiếp</p>
                        </div>
                      </div>
                      <div className="mt-5 flex min-h-0 flex-1 items-center overflow-y-auto pr-2 text-[19px] leading-9 text-[#2F4F4F] custom-scrollbar">
                        {spokenAnswer ? (
                          <p>{spokenAnswer}</p>
                        ) : (
                          <p className="text-[#9AA5A5]">
                            Bắt đầu nói, nội dung bạn trả lời sẽ hiển thị tại đây...
                          </p>
                        )}
                      </div>
                    </section>

                    <div className="mt-5 flex w-full shrink-0 items-center justify-between gap-4 rounded-full border border-[#2F4F4F]/8 bg-white px-3 py-3 shadow-[0_10px_28px_rgba(47,79,79,0.045)]">
                      <button
                        type="button"
                        onClick={cancelRecording}
                        className="px-2 text-sm font-semibold text-[#7B8787] underline-offset-4 hover:underline"
                      >
                        Hủy
                      </button>

                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={toggleRecordingPause}
                          className={`flex h-11 w-11 items-center justify-center rounded-full transition-colors ${
                            isListening
                              ? "bg-[#EAF4E6] text-[#4F9339]"
                              : "bg-[#F0F2EF] text-[#647373]"
                          }`}
                          aria-label={isListening ? "Tạm dừng ghi âm" : "Tiếp tục ghi âm"}
                        >
                          <Mic size={18} />
                        </button>

                        <button
                          type="button"
                          onClick={toggleRecordingPause}
                          className="h-11 rounded-2xl border border-[#2F4F4F]/10 bg-white px-5 text-sm font-semibold text-[#647373] transition-colors hover:bg-[#F8FAF5]"
                        >
                          {isListening ? "Tạm dừng" : "Tiếp tục"}
                        </button>

                        <button
                          type="button"
                          onClick={finishRecording}
                          className="h-11 rounded-2xl bg-[var(--primary)] px-5 text-sm font-semibold text-white shadow-sm shadow-green-900/10 transition-colors hover:bg-[#4F9339]"
                        >
                          Hoàn tất câu trả lời
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {answerMode === "review" && (
                  <div className="w-full max-w-[820px] rounded-[24px] border border-[#2F4F4F]/10 bg-[#FBFCF8] p-6 shadow-[0_10px_28px_rgba(47,79,79,0.035)] animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <h3 className="text-sm font-bold text-[#2F4F4F]">Câu trả lời của bạn</h3>
                    <div className="mt-4 min-h-[120px] text-[16px] leading-8 text-[#2F4F4F]">
                      {spokenAnswer ? (
                        <p>{spokenAnswer}</p>
                      ) : (
                        <p className="text-[#9AA5A5]">Chưa có nội dung ghi âm.</p>
                      )}
                    </div>

                    <div className="mt-5 flex items-center justify-between gap-4 border-t border-[#2F4F4F]/8 pt-4">
                      <div className="flex items-center gap-4">
                        <button
                          type="button"
                          onClick={retakeRecording}
                          className="text-sm font-semibold text-[#5A9E40] underline-offset-4 hover:underline"
                        >
                          Ghi lại
                        </button>
                        <button
                          type="button"
                          onClick={editSpokenAnswer}
                          className="text-sm font-semibold text-[#647373] underline-offset-4 hover:underline"
                        >
                          Chỉnh sửa
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={() => submitAnswer(spokenAnswer)}
                        disabled={!spokenAnswer || loading}
                        className="h-10 rounded-2xl bg-[#2F4F4F] px-5 text-sm font-semibold text-white transition-colors hover:bg-[#264242] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Gửi câu trả lời
                      </button>
                    </div>
                  </div>
                )}

                {answerMode === "typing" && (
                  <div className="w-full max-w-[820px] rounded-[24px] border border-[#2F4F4F]/10 bg-[#FBFCF8] p-5 shadow-[0_10px_28px_rgba(47,79,79,0.035)] animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <textarea
                      ref={textFallbackRef}
                      value={typedAnswer}
                      onChange={(event) => setTypedAnswer(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                          event.preventDefault();
                          submitAnswer();
                        }
                      }}
                      rows={5}
                      placeholder="Nhập câu trả lời của bạn..."
                      className="h-[132px] w-full resize-none bg-transparent text-[15px] leading-7 text-[#2F4F4F] outline-none placeholder:text-[#9AA5A5]"
                    />

                    <div className="mt-4 flex items-center justify-between gap-4 border-t border-[#2F4F4F]/8 pt-4">
                      <button
                        type="button"
                        onClick={() => {
                          switchToReady();
                        }}
                        className="text-sm font-semibold text-[#5A9E40] underline-offset-4 hover:underline"
                      >
                        Chuyển sang trả lời bằng giọng nói
                      </button>

                      <button
                        type="button"
                        onClick={() => submitAnswer(typedAnswer)}
                        disabled={!typedAnswer.trim() || loading}
                        className="h-10 rounded-2xl bg-[#2F4F4F] px-5 text-sm font-semibold text-white transition-colors hover:bg-[#264242] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Gửi câu trả lời
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </main>

          <aside className="flex min-h-0 flex-col rounded-[28px] border border-[#2F4F4F]/8 bg-white px-7 py-8 shadow-[0_14px_40px_rgba(47,79,79,0.035)]">
            <div>
              <h2 className="font-heading text-[21px] font-bold tracking-tight text-[#2F4F4F]">Huấn luyện viên AI</h2>
              <p className="mt-1 text-sm font-medium text-[#6B7A7A]">Gợi ý trước khi trả lời</p>
            </div>

            <div className="mt-7 rounded-[24px] border border-[#2F4F4F]/8 bg-[#FBFCF8] p-5">
              <h3 className="text-sm font-bold text-[#2F4F4F]">Nên bao gồm</h3>
              <ul className="mt-4 space-y-3 text-sm font-medium leading-6 text-[#425A5A]">
                <li className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                  Hành trình học tập
                </li>
                <li className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                  Một project hoặc nghiên cứu nổi bật
                </li>
                <li className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                  Lý do chọn ML / AI
                </li>
              </ul>
              <p className="mt-5 border-t border-[#2F4F4F]/8 pt-4 text-sm leading-6 text-[#5A6D6D]">
                Trả lời trong 60–90 giây. Tập trung vào hành trình, động lực và điểm nổi bật nhất.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
