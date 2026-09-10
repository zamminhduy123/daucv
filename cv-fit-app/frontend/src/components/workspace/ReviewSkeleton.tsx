import { ArrowLeft, Loader2 } from "lucide-react";

export default function ReviewSkeleton({ cvFileName }: { cvFileName?: string }) {
  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#FBFBFA]">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 bg-white border-b border-gray-100 shrink-0">
        <div className="flex items-center gap-3">
          <div className="rounded-lg p-1.5 text-gray-300">
            <ArrowLeft size={17} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-700 tracking-tight">
              {cvFileName || "CV của tôi"}
            </span>
            <div className="w-5 h-5 rounded-full bg-gray-100 animate-pulse" />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="h-7 w-20 rounded-xl bg-gray-100 animate-pulse" />
          <div className="h-7 w-28 rounded-full bg-[#2D7A58]/20 animate-pulse" />
        </div>
      </div>

      {/* Subheader Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 px-6 py-2 bg-white border-b border-gray-100 shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-7 w-32 rounded-xl bg-gray-100 animate-pulse" />
          <div className="h-4 w-px bg-gray-200" />
          <div className="h-7 w-24 rounded-xl bg-gray-100 animate-pulse" />
          <div className="h-7 w-20 rounded-xl bg-gray-100 animate-pulse" />
        </div>
        <div className="h-5 w-16 rounded-full bg-gray-100 animate-pulse" />
      </div>

      {/* Main Workspace 2-Column Split */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden relative">
        {/* Left Pane: Form Editor Skeleton */}
        <div className="w-full lg:w-1/2 flex flex-col border-r border-gray-100 bg-[#FBFBFA] min-h-0">
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {/* Section Header Card */}
            <div className="rounded-2xl border border-gray-200/80 bg-white p-5 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <div className="h-5 w-36 rounded bg-gray-200 animate-pulse" />
                <div className="h-6 w-16 rounded-lg bg-gray-100 animate-pulse" />
              </div>
              <div className="h-3 w-56 rounded bg-gray-100 animate-pulse" />
            </div>

            {/* Field Blocks Skeletons */}
            <div className="rounded-2xl border border-gray-200/80 bg-white p-5 shadow-2xs space-y-4">
              <div className="space-y-1.5">
                <div className="h-3 w-20 rounded bg-gray-100 animate-pulse" />
                <div className="h-9 w-full rounded-xl bg-gray-50 border border-gray-200/60 animate-pulse" />
              </div>
              <div className="space-y-1.5">
                <div className="h-3 w-24 rounded bg-gray-100 animate-pulse" />
                <div className="h-9 w-full rounded-xl bg-gray-50 border border-gray-200/60 animate-pulse" />
              </div>
              <div className="space-y-1.5">
                <div className="h-3 w-28 rounded bg-gray-100 animate-pulse" />
                <div className="h-20 w-full rounded-xl bg-gray-50 border border-gray-200/60 animate-pulse" />
              </div>
            </div>
          </div>
        </div>

        {/* Right Pane: A4 Document Canvas Skeleton */}
        <div className="w-full lg:w-1/2 flex flex-col bg-[#EFEFED] min-h-0 overflow-y-auto p-6 items-center">
          <div className="w-full max-w-[560px] min-h-[720px] bg-white rounded-lg shadow-sm border border-gray-200/70 p-8 space-y-6">
            <div className="text-center space-y-2">
              <div className="h-6 w-48 rounded bg-gray-200 animate-pulse mx-auto" />
              <div className="h-3 w-64 rounded bg-gray-100 animate-pulse mx-auto" />
            </div>
            <div className="border-t border-gray-100 pt-4 space-y-3">
              <div className="h-4 w-32 rounded bg-gray-200 animate-pulse" />
              <div className="h-3 w-full rounded bg-gray-100 animate-pulse" />
              <div className="h-3 w-5/6 rounded bg-gray-100 animate-pulse" />
              <div className="h-3 w-4/6 rounded bg-gray-100 animate-pulse" />
            </div>
            <div className="border-t border-gray-100 pt-4 space-y-3">
              <div className="h-4 w-28 rounded bg-gray-200 animate-pulse" />
              <div className="h-3 w-full rounded bg-gray-100 animate-pulse" />
              <div className="h-3 w-11/12 rounded bg-gray-100 animate-pulse" />
            </div>
          </div>
        </div>

        {/* Floating polite status pill */}
        <div className="pointer-events-none absolute bottom-5 left-1/2 -translate-x-1/2 z-20">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/95 border border-gray-200 px-4 py-2 text-xs font-semibold text-slate-700 shadow-lg backdrop-blur-xs">
            <Loader2 size={14} className="animate-spin text-[#2D7A58]" />
            <span>Đang chuẩn bị không gian làm việc...</span>
          </div>
        </div>
      </div>
    </div>
  );
}
