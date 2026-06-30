"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  FileText, Mic, LayoutTemplate, Clock, QrCode, Coffee,
  PenLine, PenTool, BookOpen, Briefcase, ChevronLeft, ChevronRight,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { toast } from "sonner";

const NAV_ITEMS = [
  { label: "Nhập CV & JD", icon: PenLine, href: "/app/setup", requiresCV: false },
  { label: "Phân tích CV", icon: FileText, href: "/app/analyzer", requiresCV: true },
  { label: "Tìm việc làm", icon: Briefcase, href: "/app/jobs", requiresCV: true },
  { label: "Phỏng vấn 1-1", icon: Mic, href: "/app/interview", requiresCV: true },
  { label: "Trợ lý Viết", icon: PenTool, href: "/app/writer", requiresCV: true },
  { label: "Thư viện Mẫu CV", icon: LayoutTemplate, href: "/app/templates", requiresCV: false },
  { label: "Blog & Cẩm nang", icon: BookOpen, href: "/blog", requiresCV: false },
  { label: "Lịch sử", icon: Clock, href: "/app/history", requiresCV: false },
];

// ── Collapsible Sidebar ─────────────────────────────────────────────────────

export default function AppSidebar() {
  const [showQR, setShowQR] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();
  const { cvText, isLoaded } = useWorkspace();
  const hasCV = !!cvText?.trim();

  // ── helpers ────────────────────────────────────────────────────────────────
  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");
  const isDisabled = (href: string, requiresCV: boolean) =>
    isLoaded && requiresCV && !hasCV;

  const handleNavClick = (href: string, requiresCV: boolean) => {
    if (isDisabled(href, requiresCV)) {
      toast.error("Vui lòng nhập CV của bạn trước khi sử dụng tính năng này", {
        position: "top-center",
      });
      return false; // prevent navigation
    }
    return true;
  };

  return (
    <aside
      className={`hidden md:flex flex-shrink-0 h-full bg-white border-r border-gray-100 flex-col transition-all duration-300 ease-in-out ${
        isCollapsed ? "w-[4.5rem]" : "w-64"
      }`}
    >
      {/* ── Brand ─────────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-50 px-3 py-4 flex-shrink-0">
        <Link
          href="/"
          onClick={(e) => {
            if (isCollapsed) setIsCollapsed(false);
          }}
          className="flex items-center gap-2.5 no-underline hover:opacity-80 transition-opacity"
        >
          <Image
            src="/main-icon.webp"
            alt="Đậu"
            width={isCollapsed ? 28 : 36}
            height={isCollapsed ? 28 : 36}
            style={{ width: "auto", height: "auto" }}
            className="drop-shadow-sm transition-all duration-300"
          />
          <div
            className={`flex-1 min-w-0 overflow-hidden transition-all duration-300 ${
              isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"
            }`}
          >
            <span className="font-heading font-bold text-[#2F4F4F] text-2xl tracking-tight whitespace-nowrap block">
              ĐẬU
            </span>
            <p className="text-[11px] text-gray-400 ml-[44px] whitespace-nowrap">
              AI Career Companion
            </p>
          </div>
        </Link>
      </div>

      {/* ── Nav ───────────────────────────────────────────────────────────── */}
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {/* Section label — hidden when collapsed */}
        {!isCollapsed && (
          <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 ml-2 mb-2">
            Công cụ
          </p>
        )}

        {/* CV warning — hidden when collapsed */}
        {!isCollapsed && isLoaded && !hasCV && (
          <div className="mb-3 p-2.5 bg-blue-50/50 rounded-xl border border-blue-100/50">
            <p className="text-[11px] text-blue-600 leading-relaxed font-medium">
              Nhập CV để mở khoá tính năng Phân tích & Phỏng vấn
            </p>
          </div>
        )}

        {NAV_ITEMS.map(({ label, icon: Icon, href, requiresCV }) => {
          const active = isActive(href);
          const disabled = isDisabled(href, requiresCV);

          return (
            <Link
              key={href}
              href={disabled ? "#" : href}
              title={disabled ? "Vui lòng nhập CV của bạn trước" : undefined}
              onClick={(e) => {
                if (!handleNavClick(href, requiresCV)) {
                  e.preventDefault();
                }
              }}
              className={`relative flex items-center rounded-xl text-sm font-medium
                transition-all duration-200 no-underline group
                ${isCollapsed ? "justify-center px-0 py-3" : "px-3 py-2.5  gap-3"}
                ${
                  disabled
                    ? "text-gray-400 cursor-not-allowed bg-gray-50/50"
                    : active
                    ? "bg-[var(--primary)]/10 text-[var(--primary)] font-semibold"
                    : "text-gray-500 hover:bg-gray-50 hover:text-[#2F4F4F]"
                }`}
            >
              <Icon
                size={isCollapsed ? 20 : 18}
                className={`flex-shrink-0 transition-colors duration-200 ${
                  disabled
                    ? "text-gray-300"
                    : active
                    ? "text-[var(--primary)]"
                    : "text-gray-400 group-hover:text-[#2F4F4F]"
                }`}
              />

              {/* Text label — animated fade-out */}
              <span
                className={`whitespace-nowrap overflow-hidden transition-all duration-300 ease-in-out ${
                  isCollapsed ? "w-0 opacity-0 max-w-0" : "w-auto opacity-100 max-w-none"
                }`}
              >
                {label}
              </span>

              {/* "Soon" badge — always visible */}
              {href === "/app/history" && !disabled && (
                <span
                  className={`flex-shrink-0 text-[9px] font-bold bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded-full transition-all duration-300 ${
                    isCollapsed ? "hidden" : ""
                  }`}
                >
                  Soon
                </span>
              )}

              {/* Tooltip — shown only when collapsed and hovered */}
              {isCollapsed && (
                <div className="hidden group-hover:flex absolute left-full top-1/2 -translate-y-1/2 ml-2 z-50 items-center gap-2 px-3 py-1.5 bg-[#1F2E2E] text-white text-xs font-medium rounded-lg shadow-lg whitespace-nowrap pointer-events-none">
                  {label}
                  {/* Small arrow */}
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-[#1F2E2E]" />
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── Collapse Toggle ───────────────────────────────────────────────── */}
      <div
        className={`border-t border-gray-50 py-2 flex-shrink-0 transition-all duration-300 ${
          isCollapsed ? "px-1.5" : "px-2.5 py-2"
        }`}
      >
        <button
          onClick={() => setIsCollapsed((v) => !v)}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="flex items-center justify-center gap-2 w-full text-gray-400 hover:text-[#2F4F4F] hover:bg-gray-50 rounded-lg transition-colors duration-200 cursor-pointer"
        >
          {isCollapsed ? (
            <>
              <ChevronRight size={16} className="flex-shrink-0" />
              {/* <span className="text-[11px] font-semibold whitespace-nowrap overflow-hidden transition-all duration-300 w-auto opacity-100">
                Mở rộng
              </span> */}
            </>
          ) : (
            <>
              <ChevronLeft size={16} className="flex-shrink-0" />
              <span className="text-[11px] font-semibold whitespace-nowrap overflow-hidden transition-all duration-300 w-auto opacity-100">
                Thu nhỏ
              </span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
