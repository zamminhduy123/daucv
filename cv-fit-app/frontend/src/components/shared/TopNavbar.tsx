"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import Logo from "./Logo";

interface TopNavbarProps {
  /** Left-side action — defaults to nothing (landing), pass props to show a back button */
  leftSlot?: React.ReactNode;
  /** Right-side action — defaults to nothing */
  rightSlot?: React.ReactNode;
  /** Show step indicator dots for the workspace */
  currentStep?: 1 | 2;
}

export default function TopNavbar({ leftSlot, rightSlot, currentStep }: TopNavbarProps) {
  return (
    <header className="bg-white border-b border-[#2F4F4F]/[0.08] shrink-0">
      <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between relative">
        {/* Left slot */}
        <div className="flex items-center gap-3 min-w-[140px]">
          {leftSlot}
        </div>

        {/* Centre logo — absolutely centred */}
        <div className="absolute left-1/2 -translate-x-1/2">
          <Logo size="md" />
        </div>

        {/* Right slot */}
        <div className="flex items-center gap-3 min-w-[140px] justify-end">
          {currentStep && (
            <div className="flex items-center gap-1.5 mr-2">
              {[1, 2].map((s) => (
                <div
                  key={s}
                  className="h-2 rounded-full transition-all duration-300"
                  style={{
                    width: s === currentStep ? 32 : 8,
                    backgroundColor:
                      s === currentStep ? "var(--primary)" : "rgba(47,79,79,0.15)",
                  }}
                />
              ))}
            </div>
          )}
          {rightSlot}
        </div>
      </div>
    </header>
  );
}

/** Convenience: the sticky Landing navbar */
export function LandingNavbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);
  return (
    <header
      className="max-w-7xl mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-12 py-6 lg:py-8 relative"
    >
      <Logo size="md" />
      <nav className="hidden md:flex gap-4 lg:gap-8 text-sm font-semibold">
        <Link 
          href="/" 
          className="hover-elevate px-3 py-2 rounded-xl text-[#2F4F4F] no-underline"
        >
          Trang chủ
        </Link>
        <Link 
          href="/qna" 
          className="hover-elevate px-3 py-2 rounded-xl text-[#2F4F4F] no-underline"
        >
          Hỏi đáp
        </Link>
        <Link 
          href="/blog" 
          className="hover-elevate px-3 py-2 rounded-xl text-[#2F4F4F] no-underline"
        >
          Blog
        </Link>
        {/* {["Lợi ích", "Tính năng"].map((item) => (
          <a
            key={item}
            href={`/#${item.toLowerCase().replace(" ", "-")}`}
            className="hover-elevate px-3 py-2 rounded-xl text-[#2F4F4F]/60 hover:text-[#2F4F4F] no-underline transition-colors"
          >
            {item}
          </a>
        ))} */}
      </nav>
      <div className="flex items-center gap-2">
        <Link href="/app/setup" className="inline-flex items-center rounded-xl border border-gray-200 bg-white px-4 py-2 sm:px-6 sm:py-3 text-sm sm:text-base font-bold text-[#2F4F4F] no-underline transition-all hover:shadow-md hover:border-[#2D7A58]/40">
          Bắt đầu ngay
        </Link>
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-label={menuOpen ? "Đóng menu" : "Mở menu"}
          aria-expanded={menuOpen}
          className="md:hidden rounded-xl p-2.5 text-[#2F4F4F] hover:bg-gray-100 transition-colors cursor-pointer"
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
      {menuOpen && (
        <nav className="md:hidden absolute top-full left-4 right-4 sm:left-6 sm:right-6 z-50 flex flex-col gap-1 rounded-2xl border border-gray-100 bg-white p-3 shadow-xl">
          {[
            { href: "/", label: "Trang chủ" },
            { href: "/qna", label: "Hỏi đáp" },
            { href: "/blog", label: "Blog" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={closeMenu}
              className="rounded-xl px-4 py-3 text-sm font-semibold text-[#2F4F4F] no-underline hover:bg-gray-50 transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
