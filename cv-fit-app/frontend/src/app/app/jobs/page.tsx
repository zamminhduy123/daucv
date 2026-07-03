"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { 
  Briefcase, MapPin, DollarSign, Calendar, Sparkles, ExternalLink, 
  FileText, CheckCircle2, AlertCircle, RefreshCw, 
  SlidersHorizontal, X, ShieldAlert
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

import { useWorkspace } from "@/context/WorkspaceContext";
import { searchJobsAPI, generateWritingAPI } from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";
import { RankedJobResult, JobSourceStatus, CandidateProfile } from "@/lib/jobs/types";

type DateRangeFilter = "1d" | "3d" | "7d" | "14d" | "30d";

export default function JobsPage() {
  const router = useRouter();
  const { cvText, hasData, isLoaded, updateWorkspace } = useWorkspace();

  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [jobs, setJobs] = useState<RankedJobResult[]>([]);
  const [sourceStatuses, setSourceStatuses] = useState<JobSourceStatus[]>([]);
  const [queries, setQueries] = useState<string[]>([]);

  // Filter States
  const [targetRole, setTargetRole] = useState("");
  const [location, setLocation] = useState("Tất cả");
  const [dateRange, setDateRange] = useState<DateRangeFilter>("7d");
  const [selectedSources, setSelectedSources] = useState<string[]>(["itviec", "topcv", "vietnamworks", "ybox", "glints", "jobsgo", "careerviet", "vieclam24h"]);
  const [showStretch, setShowStretch] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  // Cover Letter Modal
  const [isGeneratingLetter, setIsGeneratingLetter] = useState(false);
  const [generatedLetter, setGeneratedLetter] = useState<{ subject: string; content: string } | null>(null);
  const [selectedJobForLetter, setSelectedJobForLetter] = useState<RankedJobResult | null>(null);

  // Detailed Match Modal
  const [selectedJobForMatch, setSelectedJobForMatch] = useState<RankedJobResult | null>(null);

  // Route guard
  useEffect(() => {
    if (isLoaded && !hasData) {
      router.replace("/app/setup");
    }
  }, [isLoaded, hasData, router]);

  const handleSearch = useCallback(async (isInitial = false) => {
    if (!cvText) return;
    setIsLoading(true);
    setError("");

    try {
      console.log("=== [Job Finder] BẮT ĐẦU QUÉT VIỆC LÀM ===");
      console.log("Bước 1: Khởi tạo tham số tìm kiếm:", {
        cvTextLength: cvText.length,
        targetRoleOverride: targetRole || "None",
        locationOverride: location,
        dateRange,
        sources: selectedSources
      });

      // Step-by-step loading state
      const steps = [
        "Đang trích xuất thông tin từ CV của bạn...",
        "Đang truy vấn ITviec...",
        "Đang truy vấn TopCV...",
        "Đang quét các tin tuyển dụng VietnamWorks...",
        "Đang tìm kiếm trên Ybox...",
        "Đang tính toán mức độ tương thích & xếp hạng..."
      ];

      let stepIdx = 0;
      setLoadingStep(steps[stepIdx++]);

      const interval = setInterval(() => {
        if (stepIdx < steps.length) {
          setLoadingStep(steps[stepIdx++]);
        }
      }, 1500);

      const payload = {
        cvText,
        targetRole: targetRole || undefined,
        location: location === "Tất cả" ? undefined : location,
        dateRange,
        sources: selectedSources
      };

      console.log("Bước 2: Đang gọi Next.js API /api/jobs/search...");
      const response = await searchJobsAPI(payload);
      
      clearInterval(interval);

      console.log("Bước 3: Nhận phản hồi thành công từ API. Hồ sơ ứng viên trích xuất:", {
        targetRoles: response.profile.targetRoles,
        skills: response.profile.skills,
        seniority: response.profile.seniority,
        yearsOfExperience: response.profile.yearsOfExperience,
        location: response.profile.location
      });

      console.log("Bước 4: Kết quả quét từ các nguồn tin tuyển dụng:", response.sourceStatus);

      console.log(`Bước 5: Lọc, loại trùng và xếp hạng hoàn tất. Tìm thấy ${response.jobs.length} công việc.`);
      if (response.jobs.length > 0) {
        console.log("Bảng xếp hạng công việc phù hợp (Ranked Jobs):");
        console.table(
          response.jobs.map((job: RankedJobResult) => ({
            "Tên công việc": job.title,
            "Công ty": job.company,
            "Nguồn": job.source,
            "Mức lương": job.salary,
            "Độ khớp": `${job.matchScore}%`,
            "Phân loại": job.matchLabel === "good_match" ? "Khớp tốt" : "Thử thách"
          }))
        );
      }

      setProfile(response.profile);
      setJobs(response.jobs);
      setSourceStatuses(response.sourceStatus);
      setQueries(response.queries || []);

      // Seed filter fields with parsed values on initial load
      if (isInitial && response.profile) {
        if (response.profile.targetRoles?.[0]) {
          setTargetRole(response.profile.targetRoles[0]);
        }
        if (response.profile.location) {
          setLocation(response.profile.location);
        }
      }

      toast.success(`Tìm thấy ${response.jobs.length} công việc phù hợp!`);
    } catch (err: unknown) {
      console.error("Lỗi khi quét tìm việc làm:", err);
      setError(apiErrorMessage(err));
      toast.error(apiErrorMessage(err));
    } finally {
      setIsLoading(false);
      setLoadingStep("");
    }
  }, [cvText, dateRange, location, selectedSources, targetRole]);

  // Initial load
  const isFirstLoad = useRef(true);
  useEffect(() => {
    if (!isLoaded || !hasData || !isFirstLoad.current) return;
    isFirstLoad.current = false;
    handleSearch(true); // Perform initial search on mount
  }, [isLoaded, hasData, handleSearch]);

  const handleSourceToggle = (sourceId: string) => {
    setSelectedSources(prev => 
      prev.includes(sourceId) 
        ? prev.filter(s => s !== sourceId) 
        : [...prev, sourceId]
    );
  };

  const handleFullScan = (job: RankedJobResult) => {
    const derivedJd = `Vị trí công việc: ${job.title}\n` +
      `Công ty: ${job.company}\n` +
      `Địa điểm: ${job.location || "Việt Nam"}\n` +
      `Mức lương: ${job.salary || "Thương lượng"}\n` +
      `Kỹ năng yêu cầu: ${job.skills.join(", ") || "Không yêu cầu chi tiết"}\n\n` +
      `Mô tả sơ lược:\n${job.descriptionSnippet || "Không có mô tả chi tiết từ nguồn tuyển dụng."}`;

    updateWorkspace({
      jdText: derivedJd
    });

    toast.success("Đang chuyển sang trang Phân tích chuyên sâu với CV & JD...");
    router.push("/app/analyzer");
  };

  const generateCoverLetter = async (job: RankedJobResult) => {
    setIsGeneratingLetter(true);
    setSelectedJobForLetter(job);
    setGeneratedLetter(null);
    try {
      const jdText = `Job Title: ${job.title}\nCompany: ${job.company}\nDescription: ${job.descriptionSnippet || "No detailed description was provided by the job source."}\nRequired Skills: ${job.skills.join(", ")}`;
      
      const response = await generateWritingAPI({
        cv_text: cvText,
        jd_text: jdText,
        writing_type: "cover_letter",
        tone: "professional"
      });

      setGeneratedLetter({
        subject: response.subject_line || `Thư ứng tuyển - ${job.title}`,
        content: response.content || ""
      });
      toast.success("Đã tạo Cover Letter thành công!");
    } catch (err: unknown) {
      console.error(err);
      toast.error(apiErrorMessage(err));
    } finally {
      setIsGeneratingLetter(false);
    }
  };

  if (!isLoaded || !hasData) return null;

  // Group jobs by match label
  const goodMatches = jobs.filter(j => j.matchLabel === "good_match");
  const stretchMatches = jobs.filter(j => j.matchLabel === "stretch");

  return (
    <div className="px-2 md:px-4 py-6 relative">
      {/* Background decoration */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-emerald-100/30 rounded-full blur-3xl -z-10 pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-96 h-96 bg-teal-100/20 rounded-full blur-3xl -z-10 pointer-events-none" />

      {/* Header section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div className="flex-1 gap-2">
          <h1 className="text-3xl font-bold font-heading text-slate-800 flex items-center gap-2.5">
            <Briefcase className="w-8 h-8 text-emerald-600" />
            Tìm việc làm phù hợp
          </h1>
          <p className="text-slate-500 text-sm mt-1.5">
            Backend trích xuất các kỹ năng & vai trò trong CV của bạn để quét live các job mới nhất từ TopCV, ITviec, VietnamWorks, Ybox.
          </p>
        </div>

        <div className="flex-1 flex items-end justify-end gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all border ${
              showFilters 
                ? "bg-slate-800 border-slate-800 text-white" 
                : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            Bộ lọc nâng cao
          </button>
          <button
            onClick={() => handleSearch(false)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl text-sm font-semibold shadow-md hover:scale-[1.02] hover:shadow-lg active:scale-95 transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            Quét việc làm mới
          </button>
        </div>
      </div>

      {/* Profile Summary Card */}
      {profile && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/80 backdrop-blur-md border border-slate-100 rounded-3xl p-5 mb-8 shadow-xs flex flex-col md:flex-row gap-6 items-start justify-between"
        >
          <div className="flex-1">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
              Hồ sơ ứng viên tạm thời (Từ CV)
            </h3>
            <div className="flex flex-wrap gap-2 items-center mb-3">
              <span className="text-sm font-bold text-slate-800 bg-slate-100 px-3 py-1 rounded-lg">
                {targetRole || profile.targetRoles?.[0] || "Lập trình viên"}
              </span>
              <span className="text-xs font-semibold uppercase text-emerald-700 bg-emerald-50 border border-emerald-100 px-2.5 py-0.5 rounded-full">
                Kinh nghiệm: {profile.seniority}
              </span>
              {profile.location && (
                <span className="text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {profile.location}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-2">
              {profile.skills?.slice(0, 12).map(skill => (
                <span key={skill} className="text-xs text-slate-600 bg-slate-50 border border-slate-100 px-2 py-0.5 rounded-md">
                  {skill}
                </span>
              ))}
              {profile.skills?.length > 12 && (
                <span className="text-xs text-slate-400 font-medium px-2 py-0.5">
                  +{profile.skills.length - 12} kỹ năng khác
                </span>
              )}
            </div>

            {/* Search Queries Section */}
            {queries && queries.length > 0 && (
              <div className="mt-4 pt-3.5 border-t border-dashed border-slate-100 flex flex-wrap items-center gap-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Từ khóa quét hệ thống:</span>
                {queries.map(q => (
                  <span key={q} className="text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-100 px-2.5 py-0.5 rounded-lg">
                    &quot;{q}&quot;
                  </span>
                ))}
              </div>
            )}

            {/* Quick Scan Disclaimer inside the profile card */}
            <div className="mt-4 p-3 bg-amber-50/50 border border-amber-100/70 rounded-2xl flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="text-[11px] leading-relaxed text-slate-600">
                <strong className="text-slate-800">Thông báo Quét nhanh (Quick Scan):</strong> Kết quả tương thích được tính nhanh dựa trên kỹ năng & địa điểm. Để sửa lỗi CV và tối ưu sâu theo JD, hãy chọn <strong className="text-purple-700 font-bold">Phân tích AI</strong> trên tin tuyển dụng.
              </div>
            </div>
          </div>

          {/* Scrape source status pills */}
          <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 w-full md:w-auto md:min-w-64">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Trạng thái quét nguồn tin</h4>
            <div className="grid grid-cols-2 md:grid-cols-1 gap-2 text-xs">
              {["itviec", "topcv", "vietnamworks", "ybox", "glints", "jobsgo", "careerviet", "vieclam24h"].map(src => {
                const status = sourceStatuses.find(s => s.source === src);
                const isEnabled = selectedSources.includes(src);
                return (
                  <div key={src} className="flex items-center justify-between gap-4">
                    <span className="font-semibold text-slate-500 uppercase text-[10px]">{src}</span>
                    <div className="flex items-center gap-1.5">
                      {!isEnabled ? (
                        <span className="text-[10px] text-slate-400">Tắt</span>
                      ) : status?.status === "success" ? (
                        <span className="text-[10px] font-bold text-emerald-600 flex items-center gap-1">
                          ✓ {status.count} tin
                        </span>
                      ) : status?.status === "timeout" ? (
                        <span className="text-[10px] text-amber-600 font-medium flex items-center gap-1">
                          ⚠ Timeout
                        </span>
                      ) : status?.status === "failed" ? (
                        <span className="text-[10px] text-red-500 font-medium flex items-center gap-1" title={status.error}>
                          ✕ Blocked
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400 animate-pulse">Đang quét...</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}


      {/* Advanced Filters Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden mb-6"
          >
            <div className="bg-white border border-slate-150 rounded-3xl p-6 shadow-md grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Field 1: Target Role */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Vai trò mục tiêu</label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={e => setTargetRole(e.target.value)}
                  placeholder="Ví dụ: Frontend Developer"
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>

              {/* Field 2: Location */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Địa điểm ưa thích</label>
                <select
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                >
                  <option value="Tất cả">Tất cả tỉnh thành</option>
                  <option value="Hồ Chí Minh">Hồ Chí Minh</option>
                  <option value="Hà Nội">Hà Nội</option>
                  <option value="Đà Nẵng">Đà Nẵng</option>
                  <option value="Remote">Làm việc từ xa (Remote)</option>
                </select>
              </div>

              {/* Field 3: Date Range */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Thời gian đăng tin</label>
                <select
                  value={dateRange}
                  onChange={e => setDateRange(e.target.value as DateRangeFilter)}
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                >
                  <option value="1d">Trong 24 giờ qua</option>
                  <option value="3d">Trong 3 ngày qua</option>
                  <option value="7d">Trong 7 ngày qua (Mặc định)</option>
                  <option value="14d">Trong 14 ngày qua</option>
                  <option value="30d">Trong 30 ngày qua</option>
                </select>
              </div>

              {/* Checkboxes: Sources */}
              <div className="md:col-span-2 flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Nguồn quét</label>
                <div className="flex flex-wrap gap-4 mt-1">
                  {[
                    { id: "itviec", name: "ITviec" },
                    { id: "topcv", name: "TopCV" },
                    { id: "vietnamworks", name: "VietnamWorks" },
                    { id: "ybox", name: "Ybox" },
                    { id: "glints", name: "Glints" },
                    { id: "jobsgo", name: "JobsGO" },
                    { id: "careerviet", name: "CareerViet" },
                    { id: "vieclam24h", name: "Vieclam24h" }
                  ].map(src => (
                    <label key={src.id} className="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={selectedSources.includes(src.id)}
                        onChange={() => handleSourceToggle(src.id)}
                        className="w-4.5 h-4.5 rounded border-slate-350 text-emerald-600 focus:ring-emerald-500/20 cursor-pointer"
                      />
                      {src.name}
                    </label>
                  ))}
                </div>
              </div>

              {/* Toggle: Stretch Jobs */}
              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowStretch(!showStretch)}
                  className={`w-11 h-6 rounded-full transition-colors relative focus:outline-none ${
                    showStretch ? "bg-emerald-600" : "bg-slate-200"
                  }`}
                >
                  <span
                    className={`w-4 h-4 rounded-full bg-white absolute top-1 left-1 transition-transform ${
                      showStretch ? "translate-x-5" : ""
                    }`}
                  />
                </button>
                <span className="text-sm font-semibold text-slate-700 cursor-pointer select-none" onClick={() => setShowStretch(!showStretch)}>
                  Hiển thị Stretch Jobs (Độ khớp 50% - 70%)
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading & Loading Steps Overlay */}
      {isLoading && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex flex-col items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-sm w-full mx-4 shadow-2xl flex flex-col items-center text-center border border-slate-100">
            <div className="relative w-16 h-16 mb-4">
              <div className="w-16 h-16 rounded-full border-4 border-emerald-100 border-t-emerald-600 animate-spin" />
              <Briefcase className="w-7 h-7 text-emerald-600 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            </div>
            <h3 className="font-bold text-slate-800 text-lg">Đang quét việc làm...</h3>
            <p className="text-slate-500 text-sm mt-2 font-medium min-h-12 animate-pulse">
              {loadingStep}
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-14 h-14 bg-red-50 border border-red-100 text-red-600 rounded-full flex items-center justify-center mb-3">
            <AlertCircle size={28} />
          </div>
          <h3 className="font-bold text-slate-800 text-lg">Không thể quét việc làm</h3>
          <p className="text-slate-500 text-sm mt-1 max-w-sm">{error}</p>
          <button
            onClick={() => handleSearch(false)}
            disabled={isLoading}
            className="mt-4 px-6 py-2.5 bg-emerald-600 text-white font-semibold rounded-xl text-sm shadow hover:scale-[1.02] active:scale-98 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Results Content */}
      {!isLoading && !error && (
        <div className="space-y-10">
          {jobs.length === 0 ? (
            <div className="bg-white border border-slate-100 rounded-3xl p-12 text-center shadow-xs">
              <div className="w-16 h-16 bg-slate-50 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-4">
                <Briefcase size={32} />
              </div>
              <h3 className="font-bold text-slate-800 text-lg">Không tìm thấy công việc nào</h3>
              <p className="text-slate-500 text-sm mt-1.5 max-w-md mx-auto">
                Không tìm thấy việc làm nào khớp với kỹ năng và vai trò của bạn trong vòng {dateRange === "7d" ? "7 ngày" : dateRange} qua. Hãy thử đổi từ khoá vai trò hoặc mở rộng bộ lọc thời gian!
              </p>
            </div>
          ) : (
            <>
              {/* Group 1: Best Matches (score >= 70) */}
              {goodMatches.length > 0 && (
                <div>
                  <h2 className="text-lg font-bold font-heading text-slate-700 flex items-center gap-2 mb-4">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
                    Việc làm phù hợp nhất (Khớp tốt &gt;= 70%)
                    <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                      {goodMatches.length} job
                    </span>
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {goodMatches.map(job => (
                      <JobCard 
                        key={job.id} 
                        job={job} 
                        onGenerateLetter={generateCoverLetter} 
                        onDetailedMatch={setSelectedJobForMatch}
                        onFullScan={handleFullScan}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Group 2: Stretch Matches (score >= 50 and < 70) */}
              {showStretch && stretchMatches.length > 0 && (
                <div>
                  <h2 className="text-lg font-bold font-heading text-slate-700 flex items-center gap-2 mb-4">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                    Việc làm thử thách thêm (Stretch 50% - 70%)
                    <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-bold">
                      {stretchMatches.length} job
                    </span>
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {stretchMatches.map(job => (
                      <JobCard 
                        key={job.id} 
                        job={job} 
                        onGenerateLetter={generateCoverLetter} 
                        onDetailedMatch={setSelectedJobForMatch}
                        onFullScan={handleFullScan}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Detailed Match Modal */}
      <AnimatePresence>
        {selectedJobForMatch && (
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl max-w-lg w-full max-h-[85vh] overflow-y-auto border border-slate-100 shadow-2xl p-6 relative"
            >
              <button
                onClick={() => setSelectedJobForMatch(null)}
                className="absolute top-4 right-4 p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600 rounded-xl"
              >
                <X size={18} />
              </button>

              <div className="flex items-center gap-3 mb-4">
                <span className={`text-[10px] font-bold uppercase px-2.5 py-1 rounded-full ${
                  selectedJobForMatch.matchLabel === "good_match"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}>
                  Độ tương thích: {selectedJobForMatch.matchScore}%
                </span>
                <span className="text-[10px] font-bold uppercase text-slate-400 bg-slate-50 border border-slate-100 px-2 py-1 rounded-full">
                  Nguồn: {selectedJobForMatch.source}
                </span>
              </div>

              <h2 className="text-xl font-bold font-heading text-slate-800 pr-8">{selectedJobForMatch.title}</h2>
              <p className="text-slate-500 font-semibold text-sm mt-1">{selectedJobForMatch.company}</p>

              <hr className="my-4 border-slate-100" />

              <div className="space-y-4">
                {/* Score Breakdown Analysis */}
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Lý do chấm điểm</h4>
                  <ul className="space-y-2">
                    {selectedJobForMatch.matchReasons?.map((reason, idx) => (
                      <li key={idx} className="text-sm text-slate-700 flex items-start gap-2">
                        <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600 shrink-0 mt-0.5" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Missing Skills Warning */}
                {selectedJobForMatch.missingSkills?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Kỹ năng thiếu (Cần bổ sung vào CV)</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedJobForMatch.missingSkills.map(skill => (
                        <span key={skill} className="text-xs font-semibold text-red-700 bg-red-50 border border-red-100 px-2.5 py-1 rounded-lg flex items-center gap-1">
                          <ShieldAlert className="w-3.5 h-3.5" />
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Description Snippet */}
                {selectedJobForMatch.descriptionSnippet && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">Mô tả công việc sơ lược</h4>
                    <p className="text-xs text-slate-600 bg-slate-50 rounded-xl p-3 leading-relaxed whitespace-pre-wrap">
                      {selectedJobForMatch.descriptionSnippet}
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  onClick={() => setSelectedJobForMatch(null)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50"
                >
                  Đóng
                </button>
                <a
                  href={selectedJobForMatch.url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-5 py-2 bg-emerald-600 text-white rounded-xl text-sm font-semibold hover:bg-emerald-700 flex items-center gap-1.5"
                >
                  Ứng tuyển ngay
                  <ExternalLink size={14} />
                </a>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Cover Letter Modal */}
      <AnimatePresence>
        {selectedJobForLetter && (
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl max-w-xl w-full max-h-[85vh] overflow-y-auto border border-slate-100 shadow-2xl p-6 relative"
            >
              <button
                onClick={() => setSelectedJobForLetter(null)}
                className="absolute top-4 right-4 p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600 rounded-xl"
              >
                <X size={18} />
              </button>

              <h3 className="text-lg font-bold font-heading text-slate-800 flex items-center gap-2 mb-2">
                <Sparkles className="w-5 h-5 text-emerald-500 animate-pulse" />
                Tự động tạo Cover Letter bằng AI
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Tạo nhanh thư ứng tuyển chuyên nghiệp dựa trên CV của bạn và thông tin tuyển dụng: <strong>{selectedJobForLetter.title}</strong> tại <strong>{selectedJobForLetter.company}</strong>.
              </p>

              {isGeneratingLetter && (
                <div className="py-12 flex flex-col items-center justify-center text-center gap-3">
                  <div className="w-10 h-10 border-4 border-emerald-100 border-t-emerald-600 rounded-full animate-spin" />
                  <p className="text-sm font-semibold text-slate-600">Đang phân tích và soạn thảo bằng AI...</p>
                </div>
              )}

              {!isGeneratingLetter && generatedLetter && (
                <div className="space-y-4">
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Tiêu đề thư</label>
                    <div className="text-sm font-semibold text-slate-800 bg-slate-50 border border-slate-100 rounded-xl px-4 py-2.5 select-all">
                      {generatedLetter.subject}
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Nội dung thư</label>
                    <div className="text-xs text-slate-700 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 leading-relaxed whitespace-pre-wrap select-all font-mono max-h-72 overflow-y-auto">
                      {generatedLetter.content}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(generatedLetter.content);
                        toast.success("Đã sao chép nội dung thư!");
                      }}
                      className="flex-1 py-3 border border-emerald-600 text-emerald-700 rounded-xl text-sm font-semibold hover:bg-emerald-50 transition-colors"
                    >
                      Sao chép nội dung
                    </button>
                  </div>
                </div>
              )}

              <div className="mt-6 flex justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  onClick={() => setSelectedJobForLetter(null)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50"
                >
                  Đóng
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Job Card Component ────────────────────────────────────────────────────────
interface JobCardProps {
  job: RankedJobResult;
  onGenerateLetter: (job: RankedJobResult) => void;
  onDetailedMatch: (job: RankedJobResult) => void;
  onFullScan: (job: RankedJobResult) => void;
}

function JobCard({ job, onGenerateLetter, onDetailedMatch, onFullScan }: JobCardProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
    >
      <div>
        {/* Top bar: Source badge and match percentage radial */}
        <div className="flex justify-between items-start gap-4 mb-3">
          <div className="flex flex-wrap gap-1.5 items-center">
            {/* Source logo/badge */}
            <span className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-md ${
              job.source === "itviec" 
                ? "bg-slate-800 text-white" 
                : job.source === "topcv"
                ? "bg-emerald-100 text-emerald-800"
                : job.source === "vietnamworks"
                ? "bg-blue-100 text-blue-800"
                : "bg-red-100 text-red-800"
            }`}>
              {job.source}
            </span>

            {/* Level Badge */}
            {job.level && job.level !== "unknown" && (
              <span className="text-[10px] font-bold uppercase bg-slate-50 border border-slate-200 text-slate-500 px-2 py-0.5 rounded-md">
                {job.level}
              </span>
            )}
          </div>

          {/* Radial score circle */}
          <div className="flex items-center gap-1.5">
            <span className={`text-xs font-bold ${
              job.matchScore >= 70 ? "text-emerald-600" : "text-amber-500"
            }`}>
              {job.matchScore}% Match
            </span>
            <div className="w-2.5 h-2.5 rounded-full animate-pulse shrink-0" style={{
              backgroundColor: job.matchScore >= 70 ? "#059669" : "#D97706"
            }} />
          </div>
        </div>

        {/* Title & Company */}
        <h3 className="font-bold text-slate-800 hover:text-emerald-700 leading-snug line-clamp-2" title={job.title}>
          {job.title}
        </h3>
        <p className="text-slate-500 text-xs font-semibold mt-1">{job.company}</p>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-y-2 gap-x-4 my-4 text-slate-500 text-xs">
          <div className="flex items-center gap-1.5 min-w-0">
            <MapPin className="w-3.5 h-3.5 shrink-0 text-slate-400" />
            <span className="truncate">{job.location || "Việt Nam"}</span>
          </div>
          <div className="flex items-center gap-1.5 min-w-0">
            <DollarSign className="w-3.5 h-3.5 shrink-0 text-slate-400" />
            <span className="truncate">{job.salary || "Thương lượng"}</span>
          </div>
          <div className="flex items-center gap-1.5 min-w-0 col-span-2">
            <Calendar className="w-3.5 h-3.5 shrink-0 text-slate-400" />
            <span>Cập nhật: {job.postedText || "Mới đăng"}</span>
          </div>
        </div>

        {/* Key Skills listed on Job */}
        {job.skills && job.skills.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {job.skills.slice(0, 4).map(skill => (
              <span key={skill} className="text-[10px] font-semibold bg-slate-50 border border-slate-100 text-slate-600 px-2 py-0.5 rounded-md">
                {skill}
              </span>
            ))}
            {job.skills.length > 4 && (
              <span className="text-[10px] text-slate-400 font-medium px-1.5 py-0.5">
                +{job.skills.length - 4}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="border-t border-slate-100 pt-3.5 flex flex-wrap gap-2 justify-between">
        <div className="flex gap-1.5">
          <button
            onClick={() => onDetailedMatch(job)}
            className="p-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-xl text-xs font-semibold flex items-center justify-center"
            title="Đánh giá chi tiết"
          >
            <FileText size={15} />
          </button>
          <button
            onClick={() => onGenerateLetter(job)}
            className="px-3 py-2 border border-emerald-200 text-emerald-700 hover:bg-emerald-50 rounded-xl text-xs font-bold flex items-center gap-1"
            title="Tạo Cover Letter tự động"
          >
            <Sparkles size={13} />
            Soạn thư
          </button>
        </div>

        <div className="flex gap-1.5">
          <button
            onClick={() => onFullScan(job)}
            className="px-3 py-2 bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-700 rounded-xl text-xs font-bold flex items-center gap-1 cursor-pointer"
            title="Gửi CV và JD sang trang Phân tích chuyên sâu bằng LLM"
          >
            <Sparkles size={13} />
            Phân tích AI
          </button>
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-extrabold flex items-center gap-1 no-underline"
          >
            Nộp đơn
            <ExternalLink size={13} />
          </a>
        </div>
      </div>
    </motion.div>
  );
}
