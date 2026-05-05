const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function pingAPI() {
  const res = await fetch(`${API_URL}/`);
  return res.json();
}

export async function extractPdfAPI(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/extract-pdf`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function analyzeCVAPI(cvText: string, jdText: string) {
  const res = await fetch(`${API_URL}/api/analyze-cv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv_text: cvText, jd_text: jdText }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function sendInterviewChatAPI(
  jdText: string, 
  cvText: string, 
  chatHistory: Array<{role: string, content: string}>,
  currentQuestion: number = 1,
  totalQuestions: number = 5
) {
  const res = await fetch(`${API_URL}/api/interview/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jd_text: jdText,
      cv_text: cvText,
      chat_history: chatHistory,
      current_question: currentQuestion,
      total_questions: totalQuestions
    }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function finishInterviewAPI(jdText: string, cvText: string, chatHistory: Array<{role: string, content: string}>) {
  const res = await fetch(`${API_URL}/api/interview/finish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jd_text: jdText,
      cv_text: cvText,
      chat_history: chatHistory,
    }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function generateTTSAPI(text: string) {
  const res = await fetch(`${API_URL}/api/interview/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.blob();
}

export interface WriterPayload {
  cv_text: string;
  jd_text: string;
  writing_type: string;
  tone: string;
  custom_prompt?: string;
}

export async function generateWritingAPI(payload: WriterPayload) {
  const res = await fetch(`${API_URL}/api/writer/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

