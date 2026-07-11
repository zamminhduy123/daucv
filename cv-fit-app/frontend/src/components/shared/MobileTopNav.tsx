"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Mic, LayoutTemplate, Clock, Menu, X, Coffee, QrCode, PenLine, PenTool, BookOpen, Briefcase } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { toast } from "sonner";
import Image from "next/image";

const NAV_ITEMS = [
  { label: "Nhập CV & JD", icon: PenLine, href: "/app/setup", requiresCV: false },
  { label: "Phân tích CV", icon: FileText, href: "/app/analyzer", requiresCV: true },
  { label: "Tìm việc làm", icon: Briefcase, href: "/app/jobs", requiresCV: true },
  { label: "Phỏng vấn 1-1", icon: Mic, href: "/app/interview", requiresCV: true },
  { label: "Trợ lý Viết", icon: PenTool, href: "/app/writer", requiresCV: true },
  { label: "Thư viện Mẫu CV", icon: LayoutTemplate, href: "/app/templates", requiresCV: false },
  { label: "Blog & Cẩm nang", icon: BookOpen, href: "/blog", requiresCV: false },
  { label: "CV đã tối ưu", icon: Clock, href: "/app/history", requiresCV: false },
];


export default function MobileTopNav() {
  const [showQR, setShowQR] = useState(false);
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const { cvText, isLoaded } = useWorkspace();
  const hasCV = !!cvText?.trim();

  return (
    <>
      {/* Mobile top bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 flex-shrink-0">
        <Link href="/" className="flex items-center gap-2 no-underline">
          <Image src="/main-icon.webp" alt="Đậu" width={28} height={28} style={{ width: "auto", height: "auto" }} />
          <span className="font-heading font-bold text-[#2F4F4F] text-xl">ĐẬU</span>
        </Link>
        <button
          onClick={() => setIsOpen(true)}
          className="p-2 rounded-xl hover:bg-gray-50 transition-colors text-gray-500"
          aria-label="Open menu"
        >
          <Menu size={22} />
        </button>
      </header>

      {/* Drawer overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          onClick={() => setIsOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

          {/* Drawer */}
          <aside
            className="absolute left-0 top-0 bottom-0 w-72 bg-white flex flex-col shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-5 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Image src="/main-icon.webp" alt="Đậu" width={32} height={32} style={{ width: "auto", height: "auto" }} />
                <span className="font-heading font-bold text-[#2F4F4F] text-2xl">ĐẬU</span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-xl hover:bg-gray-50 text-gray-400"
              >
                <X size={20} />
              </button>
            </div>

            <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
              {isLoaded && !hasCV && (
                <div className="mb-4 p-3 bg-blue-50/50 rounded-xl border border-blue-100/50">
                  <p className="text-[11px] text-blue-600 leading-relaxed font-medium">
                    Nhập CV để mở khoá tính năng Phân tích & Phỏng vấn
                  </p>
                </div>
              )}
              {NAV_ITEMS.map(({ label, icon: Icon, href, requiresCV }) => {
                const isActive = pathname === href || pathname.startsWith(href + "/");
                const isDisabled = isLoaded && requiresCV && !hasCV;
                
                return (
                  <Link
                    key={href}
                    href={isDisabled ? "#" : href}
                    title={isDisabled ? "Vui lòng nhập CV của bạn trước khi sử dụng tính năng này" : undefined}
                    onClick={(e) => {
                      if (isDisabled) {
                        e.preventDefault();
                        setIsOpen(false);
                        toast.error("Vui lòng nhập CV của bạn trước khi sử dụng tính năng này", {
                          position: "top-center",
                        });
                      } else {
                        setIsOpen(false);
                      }
                    }}
                    className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all no-underline ${
                      isDisabled
                        ? "text-gray-400 cursor-not-allowed bg-gray-50/50"
                        : isActive
                        ? "bg-[var(--primary)]/10 text-[var(--primary)] font-semibold"
                        : "text-gray-500 hover:bg-gray-50 hover:text-[#2F4F4F]"
                    }`}
                  >
                    <Icon size={18} className={isDisabled ? "text-gray-300" : isActive ? "text-[var(--primary)]" : "text-gray-400"} />
                    {label}
                  </Link>
                );
              })}
            </nav>

            <div className="p-4">
              <div className="text-center relative">
                <div className="flex flex-col items-center">
                  <div className={`relative w-32 mx-auto mb-2`}>
                    <Image 
                      src={showQR ? "/qr.webp" : "/redbean.webp"} 
                      alt={showQR ? "QR Code" : "Bé Đậu"} 
                      width={128}
                      height={86}
                      priority={false}
                      className={`h-auto w-full object-contain transition-opacity duration-300 ${showQR ? "rounded-lg" : ""}`} 
                      loading="eager"
                    />
                  </div>
                  {/* <p className="text-xs font-bold text-[#1F2E2E] mb-1">
                    {showQR ? "Quét mã mời Đậu nhé!" : "Tiếp thêm may mắn cho Đậu?"}
                  </p>
                  <p className="text-[10px] text-[#2F4F4F]/80 mb-3">
                    {showQR ? "Cảm ơn bạn rất nhiều! 🌱" : "Tặng Admin một bát Chè Đậu Đỏ nhé!"}
                  </p> */}
                  <button 
                    onClick={() => setShowQR(!showQR)}
                    className="w-full flex items-center justify-center gap-1.5 bg-linear-to-r from-[#C62B22] to-[#B22222] text-white text-[10px] font-bold py-2 px-4 rounded-xl hover:opacity-90 transition-opacity"
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
        </div>
      )}
    </>
  );
}
