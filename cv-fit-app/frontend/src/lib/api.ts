import { getSession } from "next-auth/react";
import type { CVAnalysisEnvelope, CVAnalysisResponse, CVDesign, LayoutLine, SuggestedEdit, TailoredCV, TailoredCVVersion } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const TTS_API_URL = process.env.NEXT_PUBLIC_TTS_SERVICE_URL || "http://127.0.0.1:8000";
const CV_ANALYSIS_TIMEOUT_MS = 315_000;

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

export interface PdfExtractResult {
  text: string;
  layout_data: LayoutLine[];
  error?: string;
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
  return res.json() as Promise<PdfExtractResult>;
}

export async function analyzeCVAPI(cvText: string, jdText: string, layoutData: LayoutLine[] | null = null) {
  let res: Response;
  try {
    res = await fetchWithAuth(`${API_URL}/api/analyze-cv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cv_text: cvText, jd_text: jdText, layout_data: layoutData }),
      signal: AbortSignal.timeout(CV_ANALYSIS_TIMEOUT_MS),
    });
  } catch (err: unknown) {
    if (
      err instanceof DOMException &&
      (err.name === "TimeoutError" || err.name === "AbortError")
    ) {
      throw {
        type: "timeout",
        message: "CV analysis timed out. Please try again.",
        status: 504,
      } satisfies ApiError;
    }
    throw parseNetworkError(err);
  }

  if (!res.ok) {
    throw await parseApiError(res);
  }
  const payload = await res.json() as CVAnalysisEnvelope;
  return mapCVAnalysisEnvelope(payload);
}

export interface CVAnalysisProgressEvent {
  type: "progress";
  stage: "queued" | "validating" | "reconstructing" | "analyzing" | "retrying" | "finalizing";
  message: string;
  details?: { attempt?: number; total_attempts?: number };
}

type CVAnalysisStreamEvent =
  | CVAnalysisProgressEvent
  | { type: "complete"; data: CVAnalysisEnvelope }
  | { type: "error"; status: number; message: string };

function mapCVAnalysisEnvelope(payload: CVAnalysisEnvelope): CVAnalysisResponse {
  return {
    ...payload.analysis,
    tailored_cv: payload.legacy_tailored_cv,
    document_v2: payload.tailored_cv,
    source_document_v2: payload.source_document_v2,
    reconstruction_diagnostics: payload.reconstruction_diagnostics,
    tailoring_entitlement: payload.tailoring_entitlement,
  } satisfies CVAnalysisResponse;
}

function streamError(status: number, message: string): ApiError {
  if (status === 401 || status === 403) return { type: "auth_error", status, message };
  if (status === 408 || status === 504) return { type: "timeout", status, message };
  if (status === 503) return { type: "ai_overloaded", status, message };
  if (status >= 500) return { type: "server_error", status, message };
  return { type: "client_error", status, message };
}

export async function analyzeCVStreamAPI(
  cvText: string,
  jdText: string,
  layoutData: LayoutLine[] | null,
  onProgress: (event: CVAnalysisProgressEvent) => void,
  signal?: AbortSignal,
): Promise<CVAnalysisResponse> {
  let res: Response;
  try {
    res = await fetchWithAuth(`${API_URL}/api/analyze-cv/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cv_text: cvText, jd_text: jdText, layout_data: layoutData }),
      signal,
    });
  } catch (err: unknown) {
    if (
      signal?.aborted ||
      (err instanceof Error && err.name === "AbortError") ||
      (err instanceof DOMException && err.name === "AbortError")
    ) {
      throw new DOMException("The user aborted a request.", "AbortError");
    }
    throw parseNetworkError(err);
  }

  if (!res.ok) throw await parseApiError(res);
  if (!res.body) throw streamError(502, "Server không trả về luồng phân tích.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel().catch(() => {});
        throw new DOMException("The user aborted a request.", "AbortError");
      }

      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line) as CVAnalysisStreamEvent;
        if (event.type === "progress") onProgress(event);
        if (event.type === "error") throw streamError(event.status, event.message);
        if (event.type === "complete") return mapCVAnalysisEnvelope(event.data);
      }

      if (done) break;
    }
  } catch (err: unknown) {
    if (
      signal?.aborted ||
      (err instanceof Error && err.name === "AbortError") ||
      (err instanceof DOMException && err.name === "AbortError")
    ) {
      await reader.cancel().catch(() => {});
      throw new DOMException("The user aborted a request.", "AbortError");
    }
    throw err;
  }

  throw streamError(502, "Luồng phân tích kết thúc trước khi có kết quả.");
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
  language?: string;
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

export async function createTailoredCVVersionAPI(payload: { tailored_cv: TailoredCV; source_cv_text: string; suggested_edits: SuggestedEdit[]; jd_text: string; target_role?: string; company_name?: string; selected_design: CVDesign; tailoring_entitlement: string; document_v2?: import("@/types").CVDocumentV2 | null; source_document_v2?: import("@/types").CVDocumentV2 | null }) {
  const res = await fetchWithAuth(`${API_URL}/api/user/tailored-cvs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!res.ok) throw await parseApiError(res);
  return res.json() as Promise<TailoredCVVersion>;
}

export async function listTailoredCVVersionsAPI() {
  const res = await fetchWithAuth(`${API_URL}/api/user/tailored-cvs`);
  if (!res.ok) throw await parseApiError(res);
  return res.json() as Promise<{ versions: TailoredCVVersion[] }>;
}

export async function updateTailoredCVDesignAPI(id: string, selected_design: CVDesign) {
  const res = await fetchWithAuth(`${API_URL}/api/user/tailored-cvs/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ selected_design }) });
  if (!res.ok) throw await parseApiError(res);
  return res.json() as Promise<TailoredCVVersion>;
}

export async function deleteTailoredCVVersionAPI(id: string) {
  const res = await fetchWithAuth(`${API_URL}/api/user/tailored-cvs/${id}`, { method: "DELETE" });
  if (!res.ok) throw await parseApiError(res);
  return res.json() as Promise<{ success: boolean }>;
}

export async function downloadTailoredCVPDFAPI(id: string) {
  const res = await fetchWithAuth(`${API_URL}/api/user/tailored-cvs/${id}/pdf`);
  if (!res.ok) throw await parseApiError(res);
  return res.blob();
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

export async function submitFeedbackAPI(rating: number, content: string) {
  const res = await fetchWithAuth(`${API_URL}/api/user/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, content }),
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
