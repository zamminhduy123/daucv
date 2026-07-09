import { getSession } from "next-auth/react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const TTS_API_URL = process.env.NEXT_PUBLIC_TTS_SERVICE_URL || "http://127.0.0.1:8000";

// Helper wrapper that automatically attaches the NextAuth accessToken to outgoing request headers
async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const session = await getSession();
  const token = (session as { accessToken?: string })?.accessToken;

  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  options.headers = headers;

  return fetch(url, options);
}

export async function pingAPI() {
  const res = await fetch(`${API_URL}/`);
  return res.json();
}

export async function extractPdfAPI(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetchWithAuth(`${API_URL}/api/extract-pdf`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function analyzeCVAPI(cvText: string, jdText: string) {
  const res = await fetchWithAuth(`${API_URL}/api/analyze-cv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv_text: cvText, jd_text: jdText }),
  });

  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function sendInterviewChatAPI(
  jdText: string,
  cvText: string,
  chatHistory: Array<{role: string, content: string}>,
  currentQuestion: number = 1,
  totalQuestions: number = 5,
  interviewType: string = "general"
) {
  const res = await fetchWithAuth(`${API_URL}/api/interview/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jd_text: jdText,
      cv_text: cvText,
      chat_history: chatHistory,
      current_question: currentQuestion,
      total_questions: totalQuestions,
      interview_type: interviewType
    }),
  });

  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function finishInterviewAPI(
  jdText: string,
  cvText: string,
  chatHistory: Array<{role: string, content: string}>,
  interviewType: string = "general"
) {
  const res = await fetchWithAuth(`${API_URL}/api/interview/finish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jd_text: jdText,
      cv_text: cvText,
      chat_history: chatHistory,
      interview_type: interviewType
    }),
  });

  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function generateTTSAPI(text: string) {
  const res = await fetchWithAuth(`${TTS_API_URL}/api/tts/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text, self_clone: true }),
  });

  if (!res.ok) {
    throw await parseApiError(res);
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
  const res = await fetchWithAuth(`${API_URL}/api/writer/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function getUserCreditsAPI() {
  const res = await fetchWithAuth(`${API_URL}/api/user/credits`);
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function getUserProfileAPI() {
  const res = await fetchWithAuth(`${API_URL}/api/user/profile`);
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function uploadUserCVAPI(cvText: string, cvFilename: string) {
  const res = await fetchWithAuth(`${API_URL}/api/user/cv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv_text: cvText, cv_filename: cvFilename }),
  });
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function updateActiveCVTextAPI(cvText: string, cvFilename: string) {
  const res = await fetchWithAuth(`${API_URL}/api/user/cv/active`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv_text: cvText, cv_filename: cvFilename }),
  });
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function deactivateUserCVAPI(cvId: string) {
  const res = await fetchWithAuth(`${API_URL}/api/user/cv/${cvId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function listUserCVsAPI() {
  const res = await fetchWithAuth(`${API_URL}/api/user/cvs`);
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function buyCreditsAPI(packageId: string) {
  const res = await fetchWithAuth(`${API_URL}/api/billing/buy-credits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ package_id: packageId }),
  });
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function requestManualPaymentAPI(packageId: string) {
  const res = await fetchWithAuth(`${API_URL}/api/billing/request-manual-payment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ package_id: packageId }),
  });
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export async function mockConfirmPaymentAPI(
  packageId: string,
  amount: number,
  creditsToAdd: number
) {
  const res = await fetchWithAuth(`${API_URL}/api/billing/mock-confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      package_id: packageId,
      amount,
      credits_to_add: creditsToAdd
    }),
  });
  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

export interface JobSearchRequest {
  cvText: string;
  targetRole?: string;
  location?: string;
  dateRange?: "1d" | "3d" | "7d" | "14d" | "30d";
  sources?: string[];
}

export async function searchJobsAPI(payload: JobSearchRequest) {
  const res = await fetchWithAuth(`${API_URL}/api/jobs/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw await parseApiError(res);
  }
  return res.json();
}

// ── Error classification ─────────────────────────────────────────────────────

/**
 * Classify an HTTP error response into a structured error type.
 *
 * Used by consumer pages to show contextually accurate messages instead of
 * generic "Lỗi từ server" text.
 *
 * Returns:
 *   - { type: "ai_overloaded" }      → 503 with "overload" in the message
 *   - { type: "auth_error" }         → 401 / 403
 *   - { type: "timeout" }            → 408 / 504
 *   - { type: "server_error" }       → 5xx
 *   - { type: "client_error" }       → 4xx (other)
 *   - { type: "network_error" }      → fetch crashed (no response)
 */
export async function parseApiError(res: Response): Promise<ApiError> {
  const message = await res.text().catch(() => "Không thể đọc phản hồi từ server");
  const status = res.status;

  if (status === 503 && message.toLowerCase().includes("overload")) {
    return { type: "ai_overloaded", message, status };
  }
  if (status === 401 || status === 403) {
    return { type: "auth_error", message, status };
  }
  if (status === 408 || status === 504) {
    return { type: "timeout", message, status };
  }
  if (status >= 500) {
    return { type: "server_error", message, status };
  }
  if (status >= 400) {
    return { type: "client_error", message, status };
  }

  return { type: "unknown", message, status };
}

/** Thrown when a fetch call crashes (no HTTP response at all). */
export function parseNetworkError(err: unknown): ApiError {
  return {
    type: "network_error",
    message: err instanceof Error ? err.message : "Không có kết nối mạng",
    status: 0,
  };
}

export interface ApiError {
  type:
    | "ai_overloaded"
    | "auth_error"
    | "timeout"
    | "server_error"
    | "client_error"
    | "network_error"
    | "unknown";
  message: string;
  status: number;
}


