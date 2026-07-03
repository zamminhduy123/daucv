import type { ApiError } from "@/lib/api";

/** Convert an ApiError (or any thrown value) into a user-friendly Vietnamese message. */
export function apiErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "type" in err) {
    const e = err as ApiError;
    switch (e.type) {
      case "ai_overloaded":
        return "AI đang quá tải. Vui lòng thử lại sau 1–2 phút nhé!";
      case "auth_error":
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
