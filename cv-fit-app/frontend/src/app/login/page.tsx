"use client";

import React, { useEffect } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/app");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#F9F9F2] font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium text-gray-500">Đang tải...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#F9F9F2] relative overflow-hidden font-sans p-6">
      {/* Decorative blurry backgrounds */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-green-100 rounded-full filter blur-[120px] opacity-65 animate-pulse"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-100 rounded-full filter blur-[120px] opacity-65 animate-pulse"></div>

      {/* Main Glassmorphism container */}
      <div className="w-full max-w-md bg-white/70 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl p-8 md:p-10 relative z-10 flex flex-col items-center text-center">
        {/* Logo/Icon */}
        <div className="w-16 h-16 bg-[var(--primary)] text-white rounded-2xl flex items-center justify-center shadow-lg shadow-green-600/20 mb-6 animate-bounce">
          <LogIn size={28} />
        </div>

        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight mb-2">
          Đăng nhập vào Đậu
        </h1>
        <p className="text-sm text-gray-500 mb-8 max-w-xs leading-relaxed">
          Tối ưu hóa CV chuẩn ATS và luyện phỏng vấn giả định với AI thông minh.
        </p>

        {/* Google Sign In Button */}
        <button
          onClick={() => signIn("google", { callbackUrl: "/app" })}
          className="w-full py-4 px-6 bg-white hover:bg-gray-50 text-gray-700 font-semibold border border-gray-200 rounded-2xl flex items-center justify-center gap-3 transition-all duration-300 shadow-sm hover:shadow-md cursor-pointer hover:border-gray-300"
        >
          {/* SVG Google Icon */}
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="#EA4335"
              d="M12 5.04c1.62 0 3.08.56 4.22 1.64l3.15-3.15C17.45 1.68 14.93 1 12 1 7.37 1 3.4 3.65 1.5 7.5l3.8 2.95C6.2 7.23 8.87 5.04 12 5.04z"
            />
            <path
              fill="#4285F4"
              d="M23.49 12.27c0-.82-.07-1.6-.2-2.36H12v4.51h6.46c-.28 1.48-1.12 2.73-2.38 3.58l3.7 2.87c2.16-2 3.71-4.94 3.71-8.6z"
            />
            <path
              fill="#FBBC05"
              d="M5.3 14.92c-.24-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29L1.5 7.39C.54 9.3 0 11.5 0 13.82c0 2.32.54 4.52 1.5 6.43l3.8-3.33z"
            />
            <path
              fill="#34A853"
              d="M12 23c3.24 0 5.97-1.07 7.96-2.91l-3.7-2.87c-1.12.75-2.55 1.19-4.26 1.19-3.13 0-5.8-2.19-6.75-5.18l-3.8 2.95C3.4 20.35 7.37 23 12 23z"
            />
          </svg>
          Đăng nhập bằng Google
        </button>

        {/* Footer info */}
        <div className="mt-8 text-xs text-gray-400">
          Bằng việc đăng nhập, bạn đồng ý với Điều khoản dịch vụ và Chính sách bảo mật của chúng tôi.
        </div>
      </div>
    </div>
  );
}
