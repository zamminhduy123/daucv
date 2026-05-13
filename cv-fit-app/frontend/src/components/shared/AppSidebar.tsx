"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { FileText, Mic, LayoutTemplate, Clock, QrCode, Coffee, PenLine, PenTool, BookOpen } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { toast } from "sonner";

const NAV_ITEMS = [
  { label: "Nhập CV & JD", icon: PenLine, href: "/app/setup", requiresCV: false },
  { label: "Phân tích CV", icon: FileText, href: "/app/analyzer", requiresCV: true },
  { label: "Phỏng vấn 1-1", icon: Mic, href: "/app/interview", requiresCV: true },
  { label: "Trợ lý Viết", icon: PenTool, href: "/app/writer", requiresCV: true },
  { label: "Thư viện Mẫu CV", icon: LayoutTemplate, href: "/app/templates", requiresCV: false },
  { label: "Blog & Cẩm nang", icon: BookOpen, href: "/blog", requiresCV: false },
  { label: "Lịch sử", icon: Clock, href: "/app/history", requiresCV: false },
];

export default function AppSidebar() {
  const [showQR, setShowQR] = useState(false);
  const pathname = usePathname();
  const { cvText } = useWorkspace();
  const hasCV = !!cvText?.trim();

  return (
    <aside className="w-64 h-full bg-white border-r border-gray-100 flex-col hidden md:flex flex-shrink-0">
      {/* Brand Area */}
      <div className="p-6 border-b border-gray-50">
        <Link href="/" className="flex items-center gap-2.5 no-underline hover:opacity-80 transition-opacity">
          <Image
            src="/main-icon.webp"
            alt="Đậu"
            width={36}
            height={36}
            className="drop-shadow-sm"
          />
          <span className="font-heading font-bold text-[#2F4F4F] text-2xl tracking-tight">
            ĐẬU
          </span>
        </Link>
        <p className="text-[11px] text-gray-400 ml-[44px]">AI Career Companion</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 ml-2">
          Công cụ
        </p>
        
        {!hasCV && (
          <div className="mb-4 p-3 bg-blue-50/50 rounded-xl border border-blue-100/50">
            <p className="text-[11px] text-blue-600 leading-relaxed font-medium">
              Nhập CV để mở khoá tính năng Phân tích & Phỏng vấn
            </p>
          </div>
        )}
        
        {NAV_ITEMS.map(({ label, icon: Icon, href, requiresCV }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/");
          const isDisabled = requiresCV && !hasCV;
          
          return (
            <Link
              key={href}
              href={isDisabled ? "#" : href}
              title={isDisabled ? "Vui lòng nhập CV của bạn trước khi sử dụng tính năng này" : undefined}
              onClick={(e) => {
                if (isDisabled) {
                  e.preventDefault();
                  toast.error("Vui lòng nhập CV của bạn trước khi sử dụng tính năng này", {
                    position: "top-center",
                  });
                }
              }}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 no-underline group ${
                isDisabled
                  ? "text-gray-400 cursor-not-allowed bg-gray-50/50"
                  : isActive
                  ? "bg-[var(--primary)]/10 text-[var(--primary)] font-semibold"
                  : "text-gray-500 hover:bg-gray-50 hover:text-[#2F4F4F]"
              }`}
            >
              <Icon
                size={18}
                className={`flex-shrink-0 transition-colors ${
                  isDisabled ? "text-gray-300" : isActive ? "text-[var(--primary)]" : "text-gray-400 group-hover:text-[#2F4F4F]"
                }`}
              />
              {label}
              
              {/* Coming soon badge for history/templates */}
              {(href === "/app/history") && !isDisabled && (
                <span className="ml-auto text-[9px] font-bold bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded-full">
                  Soon
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Support Card UI */}
      <div className="p-4 ">
        <div className="text-center relative">
          <div className="relative z-10 flex flex-col items-center">
            <div className={`relative w-full min-h-32 mb-2`}>
              <Image
                src={showQR ? "/qr.webp" : "/redbean.webp"}
                alt={showQR ? "Mã QR chuyển khoản" : "Bé Đậu và bát chè đậu đỏ"}
                width={900}
                height={600}
                priority={false}
                className={`h-auto w-full object-contain transition-opacity duration-300 ${showQR ? "rounded-lg" : ""}`}
                loading="eager"
              />
            </div>
            {/* <p className="text-xs font-bold text-[#1F2E2E] mb-1 leading-snug">
              {showQR ? "Quét mã mời Đậu nhé!" : "Tiếp thêm may mắn cho Đậu?"}
            </p>
            <p className="text-[10px] text-[#2F4F4F]/80 mb-1 leading-relaxed">
              {showQR ? "Cảm ơn bạn rất nhiều! 🌱" : "Tặng Admin một bát Chè Đậu Đỏ để giữ lấy may mắn nhé!"}
            </p> */}
            <button 
              onClick={() => setShowQR(!showQR)}
              className="w-full flex items-center justify-center gap-1.5 bg-linear-to-r from-[#C62B22] to-[#B22222] text-white text-[10px] font-bold py-2 px-3 rounded-xl hover:scale-[1.02] transition-transform shadow-sm"
            >
              {showQR ? (
                <>
                  <Coffee size={12} />
                  Quay lại
                </>
              ) : (
                <>
                  <QrCode size={12} />
                  Tặng Chè Đậu Đỏ 🍵
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
