"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  FileText, Mic, LayoutTemplate, Clock, QrCode, Coffee,
  PenLine, PenTool, BookOpen, Briefcase, ChevronLeft, ChevronRight, MessageCircle,
  ChevronDown, LogOut, Gem, MessageSquare,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { toast } from "sonner";
import { signOut } from "next-auth/react";
import { useAuth } from "@/context/AuthContext";

const NAV_ITEMS = [
  { label: "Nhập CV & JD", icon: PenLine, href: "/app/setup", requiresCV: false },
  { label: "Phân tích CV", icon: FileText, href: "/app/analyzer", requiresCV: true },
  { label: "Tìm việc làm", icon: Briefcase, href: "/app/jobs", requiresCV: true },
  { label: "Phỏng vấn 1-1", icon: Mic, href: "/app/interview", requiresCV: true },
  { label: "Trợ lý Viết", icon: PenTool, href: "/app/writer", requiresCV: true },
  // { label: "Thư viện Mẫu CV", icon: LayoutTemplate, href: "/app/templates", requiresCV: false },
  { label: "Blog & Cẩm nang", icon: BookOpen, href: "/blog", requiresCV: false },
  // { label: "CV đã tối ưu", icon: Clock, href: "/app/history", requiresCV: false },
];

// ── Collapsible Sidebar ─────────────────────────────────────────────────────

export default function AppSidebar() {
  const [showQR, setShowQR] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const pathname = usePathname();
  const { cvText, isLoaded, setFeedbackOpen } = useWorkspace();
  const hasCV = !!cvText?.trim();
  const { user, credits } = useAuth();

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
      className={`hidden md:flex shrink-0 h-full bg-white border-r border-gray-100 flex-col transition-all duration-300 ease-in-out ${
        isCollapsed ? "w-[4.5rem]" : "w-64"
      }`}
    >
      {/* ── Brand ─────────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-50 px-3 py-4 shrink-0">
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
                className={`shrink-0 transition-colors duration-200 ${
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

      {!isCollapsed ? (
        <>
          {/* Top: Feedback and Collapse row */}
          <div className="flex items-center justify-between gap-1 px-3 py-1.5 shrink-0 border-t border-gray-100">
            <button
              onClick={() => setFeedbackOpen(true)}
              title="Góp ý & Báo lỗi"
              className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer border border-transparent flex gap-1 bg-transparent"
            >
              <MessageSquare size={16} />
              <span className="text-xs">Góp ý</span>
            </button>
            <button
              onClick={() => {
                setIsCollapsed(true);
                setIsProfileOpen(false);
              }}
              aria-label="Collapse sidebar"
              title="Thu nhỏ thanh bên"
              className="p-1.5 text-gray-400 hover:text-[#2F4F4F] hover:bg-gray-100 rounded-lg transition-colors cursor-pointer border border-transparent"
            >
              <ChevronLeft size={16} />
            </button>
          </div>

          {/* Middle: Credits Compact warning-tinted Card */}
          <div className="shrink-0 px-3 py-1">
            <div className="bg-[#FFF8E6] border border-[#F5E1A9] rounded-xl p-2.5 flex items-center justify-between shadow-xs">
              <div className="flex items-center gap-1.5">
                <Gem size={14} className="text-[#B37400] fill-[#B37400]/5 shrink-0" />
                <span className="text-xs font-bold text-[#8A5C00]">{credits !== null ? credits : "—"} credits</span>
              </div>
              <Link
                href="/app/billing"
                className="text-[10px] font-bold text-[#8A5C00] bg-white hover:bg-amber-50 border border-[#D1A64E]/50 px-2 py-0.5 rounded-lg no-underline shadow-xs transition-colors cursor-pointer"
              >
                + top up
              </Link>
            </div>
          </div>

          {/* Bottom: Tappable Profile block */}
          {user && (
            <div className="shrink-0 p-3">
              <div
                onClick={() => setIsProfileOpen((v) => !v)}
                className={`p-2 flex items-center gap-3 transition-all select-none cursor-pointer border ${
                  isProfileOpen
                    ? "bg-gray-50 border-gray-100 shadow-2xs rounded-xl"
                    : "border-transparent hover:bg-gray-50/70 rounded-xl"
                }`}
              >
                {user.image ? (
                  <Image
                    src={user.image}
                    alt={user.name || "Avatar"}
                    width={32}
                    height={32}
                    className="rounded-full border border-gray-200 shadow-xs"
                  />
                ) : (
                  <div className="w-8 h-8 bg-(--primary) text-white text-xs font-bold rounded-full flex items-center justify-center">
                    {user.name?.[0]?.toUpperCase() || "U"}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-bold text-gray-700 block truncate text-left">{user.name}</span>
                </div>
                <ChevronDown
                  size={14}
                  className={`text-gray-400 transition-transform duration-300 shrink-0 ${
                    isProfileOpen ? "rotate-180" : ""
                  }`}
                />
              </div>

              {/* Collapsible Details */}
              {isProfileOpen && (
                <div className="mt-1.5 p-1 bg-gray-50/70 border border-gray-100 rounded-xl flex flex-col gap-0.5 shadow-2xs">
                  <span className="text-[10px] text-gray-400 block truncate px-2.5 py-1 text-left select-text">
                    {user.email}
                  </span>
                  <div className="h-[1px] bg-gray-200/50 my-0.5 mx-2" />
                  <button
                    onClick={() => signOut({ callbackUrl: "/" })}
                    className="flex items-center gap-2 w-full text-left px-2.5 py-1.5 text-xs text-red-500 hover:text-red-600 hover:bg-red-50/80 rounded-lg transition-colors cursor-pointer font-semibold"
                  >
                    <LogOut size={12} className="shrink-0" />
                    Đăng xuất
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <>
          {/* Collapsed Top: Stacked buttons */}
          <div className="flex flex-col items-center gap-1.5 py-2 px-1 shrink-0 border-t border-gray-100">
            <button
              onClick={() => setIsCollapsed(false)}
              aria-label="Expand sidebar"
              title="Mở rộng thanh bên"
              className="p-1.5 text-gray-400 hover:text-[#2F4F4F] hover:bg-gray-100 rounded-lg transition-colors cursor-pointer border border-transparent"
            >
              <ChevronRight size={16} />
            </button>
            <button
              onClick={() => setFeedbackOpen(true)}
              title="Góp ý & Báo lỗi"
              className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer border border-transparent bg-transparent"
            >
              <MessageSquare size={16} />
            </button>
          </div>

          {/* Collapsed Middle: Credits Badge */}
          <div className="px-1.5 py-1 shrink-0">
            <Link
              href="/app/billing"
              className="flex flex-col items-center justify-center py-2 rounded-xl text-[#8A5C00] hover:bg-[#FFF3D1] transition-colors border border-[#F5E1A9]/60 bg-[#FFF8E6] no-underline cursor-pointer shadow-2xs"
              title="Xem số dư và Nạp credit"
            >
              <Gem size={12} className="text-[#B37400] mb-0.5" />
              <span className="font-extrabold text-[10px]">{credits !== null ? credits : "—"}</span>
            </Link>
          </div>

          {/* Collapsed Bottom: Profile Avatar button */}
          {user && (
            <div className="p-2 flex justify-center shrink-0">
              <button
                onClick={() => {
                  if (confirm(`Bạn có muốn đăng xuất tài khoản ${user.name}?`)) {
                    signOut({ callbackUrl: "/" });
                  }
                }}
                title={`Đăng xuất (${user.name})`}
                className="relative group p-0 bg-transparent border-0 cursor-pointer rounded-full outline-none"
              >
                {user.image ? (
                  <Image
                    src={user.image}
                    alt={user.name || "Avatar"}
                    width={28}
                    height={28}
                    className="rounded-full border border-gray-200 shadow-sm hover:ring-2 hover:ring-red-300 transition-all"
                  />
                ) : (
                  <div className="w-7 h-7 bg-[var(--primary)] text-white text-xs font-bold rounded-full flex items-center justify-center hover:ring-2 hover:ring-red-300 transition-all">
                    {user.name?.[0]?.toUpperCase() || "U"}
                  </div>
                )}
              </button>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
