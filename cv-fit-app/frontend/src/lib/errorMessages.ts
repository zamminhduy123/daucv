import type { ApiError } from "@/lib/api";

/** Convert an ApiError (or any thrown value) into a user-friendly Vietnamese message. */
export function apiErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "type" in err) {
    const e = err as ApiError;
    switch (e.type) {
      case "ai_overloaded":
        return "AI đang quá tải. Vui lòng thử lại sau 1–2 phút nhé!";
      case "auth_error":
        if (
          e.message?.toLowerCase().includes("credit") ||
          e.message?.toLowerCase().includes("lượt")
        ) {
          return e.message;
        }
        return "Phiên làm việc hết hạn. Vui lòng đăng nhập lại.";
      case "timeout":
        return "Yêu cầu hết thời gian chờ. Vui lòng thử lại!";
      case "network_error":
        return "Mất kết nối mạng. Vui lòng kiểm tra internet và thử lại!";
      case "server_error":
        return "Lỗi từ server. Vui lòng thử lại!";
      case "client_error":
        return "Dữ liệu không hợp lệ. Vui lòng kiểm tra lại!";
      default:
        return "Đã có lỗi xảy ra. Vui lòng thử lại!";
    }
  }
  return "Đã có lỗi xảy ra. Vui lòng thử lại!";
}

/** Serialize any thrown value for console logging. Native Error instances
 * (TypeError from failed fetch, SyntaxError, ...) have non-enumerable
 * message/stack, so logging them raw prints as "{}" under Turbopack. */
export function formatCaughtError(err: unknown): string {
  if (err instanceof Error) {
    return `${err.name}: ${err.message}${err.stack ? `\n${err.stack}` : ""}`;
  }
  try {
    return JSON.stringify(err);
  } catch {
    return String(err);
  }
}

/** UI message for errors that never got an ApiError shape (most commonly a
 * fetch-level failure: backend down, restart, or CORS). */
export function connectivityMessage(err: unknown): string {
  if (err instanceof TypeError) {
    return "Mất kết nối mạng. Vui lòng kiểm tra internet và thử lại!";
  }
  return apiErrorMessage(err);
}
