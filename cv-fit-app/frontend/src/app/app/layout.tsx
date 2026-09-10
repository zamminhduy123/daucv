"use client";

import AppSidebar from "@/components/shared/AppSidebar";
import MobileTopNav from "@/components/shared/MobileTopNav";
import FeedbackModal from "@/components/shared/FeedbackModal";
import { WorkspaceProvider, useWorkspace } from "@/context/WorkspaceContext";
import { FileText, Briefcase, RefreshCw, ChevronDown, Check, Upload, Loader2, X, Trash2 } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { pingAPI, extractPdfAPI } from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";

function TopBar() {
  const { cvFileName, jdText, jdFileName, hasData, selectedCvId, cvList, isCvListLoading, selectCV, refreshCvList, updateWorkspace } = useWorkspace();
  const router = useRouter();
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);
  const [jdOpen, setJdOpen] = useState(false);
  const jdRef = useRef<HTMLDivElement>(null);
  const jdFileInputRef = useRef<HTMLInputElement>(null);
  const [jdDraft, setJdDraft] = useState(jdText);
  const [jdDraftName, setJdDraftName] = useState<string | null>(null);
  const [isExtractingJd, setIsExtractingJd] = useState(false);
  const [jdError, setJdError] = useState<string | null>(null);

  // Pill label: uploaded PDF filename wins; otherwise the first words of the
  // JD text; never blank, never just an ellipsis.
  const jdLabel = (() => {
    if (jdFileName) return jdFileName.replace(/\.pdf$/i, "");
    const firstLine = jdText.trim().split("\n")[0]?.trim() ?? "";
    if (!firstLine) return "JD đang chọn";
    return firstLine.length > 28 ? firstLine.slice(0, 28) + "…" : firstLine;
  })();

  useEffect(() => {
    if (!pickerOpen && !jdOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
      if (jdRef.current && !jdRef.current.contains(e.target as Node)) {
        setJdOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [pickerOpen, jdOpen]);

  const openPicker = () => {
    if (cvList.length === 0 && !isCvListLoading) {
      void refreshCvList();
    }
    setPickerOpen((v) => !v);
  };

  return (
    <div className="flex-0 py-3 bg-white border-b border-gray-100 items-center justify-between px-6 shrink-0 hidden md:flex">
      {/* Left: active context pills */}
      <div className="flex gap-3 text-sm font-medium">
        <div className="relative" ref={pickerRef}>
          <button
            type="button"
            onClick={openPicker}
            disabled={isCvListLoading && cvList.length === 0}
            title={hasData ? cvFileName : "Chưa chọn CV"}
            className={`px-3 py-1.5 rounded-full flex items-center gap-2 text-xs font-semibold transition-colors ${
              hasData
                ? "bg-green-50 text-[var(--primary)] hover:bg-green-100"
                : "bg-gray-50 text-gray-400"
            } disabled:opacity-60`}
          >
            <FileText size={13} />
            <span className="max-w-44 truncate">{hasData ? cvFileName : "Chưa chọn CV"}</span>
            <ChevronDown size={12} className="opacity-60" />
          </button>
          {pickerOpen && (
            <div className="absolute left-0 top-full z-50 mt-2 w-72 rounded-2xl border border-[#2F4F4F]/8 bg-white p-2 shadow-lg">
              <div className="max-h-64 overflow-y-auto space-y-1">
                {isCvListLoading && cvList.length === 0 ? (
                  <p className="px-3 py-3 text-xs text-gray-400">Đang tải danh sách CV...</p>
                ) : cvList.length === 0 ? (
                  <p className="px-3 py-3 text-xs text-gray-400">Bạn chưa có CV nào.</p>
                ) : (
                  cvList.map((cv) => {
                    const selected = cv.id === selectedCvId;
                    return (
                      <button
                        key={cv.id}
                        type="button"
                        onClick={() => {
                          selectCV(cv.id);
                          setPickerOpen(false);
                        }}
                        className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs transition-colors ${
                          selected ? "bg-[#6A9B5E]/5 font-bold text-[#2F4F4F]" : "text-gray-600 hover:bg-gray-50"
                        }`}
                      >
                        <span className="min-w-0 flex-1 truncate">{cv.cv_filename}</span>
                        {selected && <Check size={13} className="text-[#6A9B5E] shrink-0" />}
                      </button>
                    );
                  })
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  setPickerOpen(false);
                  router.push("/app/setup");
                }}
                className="mt-1 w-full rounded-xl px-3 py-2 text-left text-xs font-bold text-[var(--primary)] hover:bg-green-50"
              >
                Xem tất cả →
              </button>
            </div>
          )}
        </div>
        {hasData ? (
          <div className="relative" ref={jdRef}>
            <button
              type="button"
              onClick={() => {
                setJdDraft(jdText);
                setJdDraftName(jdFileName);
                setJdError(null);
                setJdOpen((v) => !v);
              }}
              title={jdLabel}
              className="bg-blue-50 text-blue-600 px-3 py-1.5 rounded-full flex items-center gap-2 text-xs font-semibold hover:bg-blue-100 transition-colors cursor-pointer shrink-0"
            >
              <Briefcase size={13} className="shrink-0" />
              <span className="max-w-44 truncate">
                {jdLabel}
              </span>
              <ChevronDown size={12} className="opacity-60" />
            </button>
            {jdOpen && (
              <div className="absolute left-0 top-full z-50 mt-2 w-80 rounded-2xl border border-[#2F4F4F]/8 bg-white p-3 shadow-lg">
                <div className="flex items-center justify-between px-1 pb-2">
                  <p className="text-xs font-bold text-slate-700">Job Description</p>
                  <button
                    type="button"
                    onClick={() => setJdOpen(false)}
                    className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"
                    aria-label="Đóng"
                  >
                    <X size={14} />
                  </button>
                </div>
                <input
                  ref={jdFileInputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
                      setJdError("JD: vui lòng tải lên file PDF.");
                      return;
                    }
                    if (f.size > 10 * 1024 * 1024) {
                      setJdError("JD: file quá lớn. Giới hạn 10 MB.");
                      return;
                    }
                    setIsExtractingJd(true);
                    setJdError(null);
                    extractPdfAPI(f, "jd", undefined)
                      .then((result) => {
                        if (result.error || !result.text?.trim()) {
                          throw new Error("Không đọc được nội dung PDF. Hãy dán text trực tiếp.");
                        }
                        setJdDraft(result.text.trim());
                        setJdDraftName(f.name);
                      })
                      .catch((err: unknown) => setJdError(apiErrorMessage(err)))
                      .finally(() => setIsExtractingJd(false));
                  }}
                />
                <button
                  type="button"
                  onClick={() => jdFileInputRef.current?.click()}
                  disabled={isExtractingJd}
                  className="flex w-full items-center gap-2 rounded-xl border border-dashed border-blue-200 px-3 py-2 text-left text-xs text-gray-500 hover:border-blue-400 disabled:opacity-50 cursor-pointer"
                >
                  {isExtractingJd ? <Loader2 size={13} className="animate-spin text-blue-600" /> : <Upload size={13} className="text-blue-500" />}
                  <span className="truncate">{jdDraftName ?? "Tải PDF JD"}</span>
                </button>
                <textarea
                  value={jdDraft}
                  onChange={(e) => setJdDraft(e.target.value)}
                  onBlur={() => setJdDraft((v) => v.trim())}
                  placeholder="Dán nội dung JD vào đây..."
                  rows={6}
                  className="mt-2 w-full resize-y rounded-xl border border-gray-200 px-3 py-2 text-xs text-slate-800 placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/10"
                />
                <p className="px-1 pt-1 text-[11px] text-gray-400">{jdDraft.trim().length} ký tự</p>
                {jdError && (
                  <p role="alert" className="mt-2 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-[11px] text-red-700">
                    {jdError}
                  </p>
                )}
                <div className="mt-2 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      updateWorkspace({ jdText: "", jdFileName: null });
                      setJdDraft("");
                      setJdDraftName(null);
                      setJdOpen(false);
                    }}
                    className="inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-[11px] font-bold text-gray-400 hover:text-[#B22222] hover:bg-red-50 cursor-pointer"
                  >
                    <Trash2 size={12} />
                    Xóa JD
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      updateWorkspace({ jdText: jdDraft.trim(), jdFileName: jdDraftName });
                      setJdOpen(false);
                    }}
                    className="rounded-xl bg-blue-600 px-4 py-1.5 text-[11px] font-bold text-white hover:bg-blue-700 cursor-pointer"
                  >
                    Lưu JD
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-400 self-center">Chưa có dữ liệu — hãy nhập CV và JD để bắt đầu.</span>
        )}
      </div>

      {/* Right: change data button */}
      {hasData && <button
        onClick={() => router.push("/app/setup")}
        className="flex items-center gap-1.5 text-xs text-gray-500 font-medium border border-gray-200 rounded-xl px-3 py-1.5 hover:bg-gray-50 transition-colors"
      >
        <RefreshCw size={12} />
        Thay đổi dữ liệu
      </button>}
    </div>
  );
}

import { useAuth } from "@/context/AuthContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isReviewPage = pathname === "/app/review" || pathname?.startsWith("/app/review/");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  useEffect(() => {
    // Ping backend to wake up Render instance
    pingAPI().catch(() => {});
  }, []);

  if (status === "loading") {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-[#F9F9F2]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium text-gray-500 font-sans">Đang tải...</p>
        </div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return null; // Will redirect in useEffect
  }

  return (
    <WorkspaceProvider>
      <div className="h-screen w-full flex overflow-hidden bg-[#FBFBFA]">
        {/* Persistent Left Sidebar (desktop only) */}
        <AppSidebar />

        {/* Right: Main Content Area */}
        <div className="flex-1 h-full flex flex-col overflow-hidden">
          {/* Mobile top nav (hidden on desktop) */}
          <MobileTopNav />

          {/* Desktop top bar - hidden on review workspace page */}
          {!isReviewPage && <TopBar />}

          {/* Scrollable content */}
          <main className={`flex-1 ${isReviewPage ? "overflow-hidden bg-[#FBFBFA] p-0" : "overflow-y-auto bg-[#F9F9F2] p-4"}`}>
            {children}
          </main>
        </div>
      </div>
      <FeedbackModal />
    </WorkspaceProvider>
  );
}
