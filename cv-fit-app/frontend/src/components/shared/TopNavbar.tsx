import Link from "next/link";
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
  return (
    <header
      className="max-w-7xl mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-12 py-6 lg:py-8"
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
        {["Lợi ích", "Tính năng"].map((item) => (
          <a
            key={item}
            href={`/#${item.toLowerCase().replace(" ", "-")}`}
            className="hover-elevate px-3 py-2 rounded-xl text-[#2F4F4F]/60 hover:text-[#2F4F4F] no-underline transition-colors"
          >
            {item}
          </a>
        ))}
      </nav>
      <Link href="/app" className="btn-green text-sm sm:text-base px-4 py-2 sm:px-6 sm:py-3">
        Bắt đầu ngay
      </Link>
    </header>
  );
}
