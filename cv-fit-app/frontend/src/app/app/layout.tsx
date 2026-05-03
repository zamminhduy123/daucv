"use client";

import AppSidebar from "@/components/shared/AppSidebar";
import MobileTopNav from "@/components/shared/MobileTopNav";
import { WorkspaceProvider, useWorkspace } from "@/context/WorkspaceContext";
import { FileText, Briefcase, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

function TopBar() {
  const { cvFileName, jdText, hasData } = useWorkspace();
  const router = useRouter();

  return (
    <div className="h-14 bg-white border-b border-gray-100 items-center justify-between px-6 shrink-0 hidden md:flex">
      {/* Left: active context pills */}
      <div className="flex gap-3 text-sm font-medium">
        {hasData ? (
          <>
            <span className="bg-green-50 text-[var(--primary)] px-3 py-1.5 rounded-full flex items-center gap-2 text-xs font-semibold">
              <FileText size={13} />
              {cvFileName}
            </span>
            <span className="bg-blue-50 text-blue-600 px-3 py-1.5 rounded-full flex items-center gap-2 text-xs font-semibold">
              <Briefcase size={13} />
              {jdText.trim().length > 30 ? jdText.trim().slice(0, 30) + "…" : "JD đang chọn"}
            </span>
          </>
        ) : (
          <span className="text-xs text-gray-400">Chưa có dữ liệu — hãy nhập CV và JD để bắt đầu.</span>
        )}
      </div>

      {/* Right: change data button */}
      <button
        onClick={() => router.push("/app/setup")}
        className="flex items-center gap-1.5 text-xs text-gray-500 font-medium border border-gray-200 rounded-xl px-3 py-1.5 hover:bg-gray-50 transition-colors"
      >
        <RefreshCw size={12} />
        Thay đổi dữ liệu
      </button>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <div className="h-screen w-full flex overflow-hidden">
        {/* Persistent Left Sidebar (desktop only) */}
        <AppSidebar />

        {/* Right: Main Content Area */}
        <div className="flex-1 h-full flex flex-col overflow-hidden">
          {/* Mobile top nav (hidden on desktop) */}
          <MobileTopNav />

          {/* Desktop top bar */}
          <TopBar />

          {/* Scrollable content */}
          <main className="flex-1 h-full overflow-y-auto bg-[#F9F9F2] p-4 md:p-8">
            {children}
          </main>
        </div>
      </div>
    </WorkspaceProvider>
  );
}
