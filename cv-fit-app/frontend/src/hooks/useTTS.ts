import { useEffect, useRef, useState } from "react";
import { generateTTSAPI } from "@/lib/api";

export function useTTS() {
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastSpokenRef = useRef<string | null>(null);

  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsSpeaking(false);
  };

  const speak = async (text: string) => {
    if (typeof window === "undefined" || !voiceEnabled) return;
    
    const cleanText = text.trim();
    if (!cleanText) return;
    
    // lastSpokenRef is no longer strictly used for blocking to allow manual replay, 
    // but we can still use it for tracking if needed.
    lastSpokenRef.current = cleanText;

    try {
      stopSpeaking();
      setIsLoading(true);

      const blob = await generateTTSAPI(cleanText);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setIsSpeaking(false);
      };

      setIsLoading(false);
      setIsSpeaking(true);
      await audio.play();
    } catch (err) {
      console.error("TTS Hook Error:", err);
      setIsLoading(false);
      setIsSpeaking(false);
    }
  };

  // Stop audio if voice is disabled mid-speech
  useEffect(() => {
    if (!voiceEnabled) {
      stopSpeaking();
    }
  }, [voiceEnabled]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
    };
  }, []);

  return {
    voiceEnabled,
    setVoiceEnabled,
    isSpeaking,
    isLoading,
    speak,
    stopSpeaking
  };
}
