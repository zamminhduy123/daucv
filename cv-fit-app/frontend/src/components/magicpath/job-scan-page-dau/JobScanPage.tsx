"use client";
/* eslint-disable @next/next/no-img-element -- job boards provide dynamic remote logo URLs that cannot be preconfigured for Next image optimization. */

import { useMemo, useState } from "react";
import {
  AlertCircle,
  Banknote,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleUserRound,
  ExternalLink,
  Globe2,
  Info,
  Mail,
  MapPin,
  Radar,
  RefreshCw,
  Search,
  SlidersHorizontal,
  TrendingUp,
  UserRound,
  X,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import type {
  CandidateProfile,
  JobSourceStatus,
  RankedJobResult,
} from "@/lib/jobs/types";

export type DateRangeFilter = "1d" | "3d" | "7d" | "14d" | "30d";

type GeneratedLetter = { subject: string; content: string } | null;
type SortMode = "match" | "newest" | "salary";

interface JobScanPageProps {
  profile: CandidateProfile | null;
  jobs: RankedJobResult[];
  sourceStatuses: JobSourceStatus[];
  queries: string[];
  isLoading: boolean;
  loadingStep: string;
  error: string;
  targetRole: string;
  location: string;
  dateRange: DateRangeFilter;
  selectedSources: string[];
  showStretch: boolean;
  selectedJobForLetter: RankedJobResult | null;
  generatedLetter: GeneratedLetter;
  isGeneratingLetter: boolean;
  onTargetRoleChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onDateRangeChange: (value: DateRangeFilter) => void;
  onSourceToggle: (sourceId: string) => void;
  onShowStretchChange: (value: boolean) => void;
  onSearch: () => void;
  onGenerateLetter: (job: RankedJobResult) => void;
  onFullScan: (job: RankedJobResult) => void;
  onCloseLetter: () => void;
}

const SOURCE_OPTIONS = [
  { id: "itviec", name: "ITviec" },
  { id: "topcv", name: "TopCV" },
  { id: "vietnamworks", name: "VietnamWorks" },
  { id: "ybox", name: "Ybox" },
  { id: "glints", name: "Glints" },
  { id: "jobsgo", name: "JobsGO" },
  { id: "careerviet", name: "CareerViet" },
  { id: "vieclam24h", name: "Vieclam24h" },
];

const scoreClass = (score: number) => {
  if (score >= 90) return "bg-green-500";
  if (score >= 80) return "bg-green-400";
  if (score >= 70) return "bg-lime-500";
  if (score >= 60) return "bg-amber-400";
  return "bg-amber-300";
};

const scoreLabel = (score: number) => {
  if (score >= 85) return "Phù hợp rất tốt";
  if (score >= 70) return "Phù hợp tốt";
  return "Việc làm Stretch";
};

const normalized = (value: string) => value.trim().toLocaleLowerCase("vi");

const matchedSkills = (job: RankedJobResult) => {
  const missing = new Set(job.missingSkills.map(normalized));
  return job.skills.filter((skill) => !missing.has(normalized(skill)));
};

const postedAge = (value?: string) => {
  const text = normalized(value || "");
  if (text.includes("hôm nay") || text.includes("mới đăng") || text.includes("giờ")) {
    return 0;
  }
  const number = Number.parseInt(text.match(/\d+/)?.[0] || "999", 10);
  if (text.includes("tuần")) return number * 7;
  if (text.includes("tháng")) return number * 30;
  return number;
};

const salaryValue = (value?: string) => {
  const numbers = (value || "").replaceAll(",", "").match(/\d+/g);
  return numbers ? Math.max(...numbers.map(Number)) : 0;
};

const companyInitials = (company?: string) => {
  const words = (company || "")
    .split(/\s+/)
    .filter((word) => word && !/^(công ty|company|co\.?|ltd\.?|jsc)$/i.test(word));
  return (words.slice(0, 2).map((word) => word[0]).join("") || "?").toUpperCase();
};

function CompanyLogo({
  company,
  logoUrl,
  className,
}: {
  company?: string;
  logoUrl?: string | null;
  className: string;
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const label = company || "Không rõ công ty";

  if (logoUrl && !imageFailed) {
    return (
      <div className={`overflow-hidden border border-[#e1e9df] bg-white ${className}`}>
        <img
          src={logoUrl}
          alt={`Logo ${label}`}
          loading="lazy"
          onError={() => setImageFailed(true)}
          className="h-full w-full object-contain p-1"
        />
      </div>
    );
  }

  return (
    <div
      aria-label={`Biểu tượng ${label}`}
      className={`flex items-center justify-center bg-[#edf6ea] text-xs font-extrabold text-[#5b8a53] ${className}`}
    >
      {companyInitials(company)}
    </div>
  );
}

function DetailPanel({
  job,
  onClose,
  onFullScan,
  onGenerateLetter,
}: {
  job: RankedJobResult;
  onClose: () => void;
  onFullScan: (job: RankedJobResult) => void;
  onGenerateLetter: (job: RankedJobResult) => void;
}) {
  return (
    <>
      <button
        type="button"
        aria-label="Đóng chi tiết việc làm"
        onClick={onClose}
        className="fixed inset-0 z-40 cursor-default bg-black/20"
      />
      <aside
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[390px] flex-col rounded-l-2xl bg-white shadow-2xl"
        aria-label="Chi tiết việc làm"
      >
        <div className="flex items-center gap-3 border-b border-[#edf0eb] px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-[#617070] hover:bg-[#f2f6f0]"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
          <h2 className="text-lg font-extrabold text-[#2F4F4F]">Chi tiết việc làm</h2>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6">
          <div className="flex flex-col items-center">
            <div className="flex h-24 w-24 items-center justify-center rounded-full border-[7px] border-[#d8ecd4] bg-[#6A9B5E] text-2xl font-black text-white">
              {job.matchScore}%
            </div>
            <p className="mt-2 text-sm font-bold text-[#6A9B5E]">
              {scoreLabel(job.matchScore)}
            </p>
          </div>

          <div className="mt-6">
            <div className="flex items-start gap-3">
              <CompanyLogo
                company={job.company}
                logoUrl={job.companyLogoUrl}
                className="h-11 w-11 shrink-0 rounded-xl"
              />
              <div className="min-w-0">
                <h3 className="text-xl font-extrabold text-[#2F4F4F]">{job.title}</h3>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-[#687878]">
                  <span>{job.company || "Không rõ công ty"}</span>
                  <span className="rounded-full bg-[#f0f2f1] px-2 py-0.5 text-xs">
                    {job.source}
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-[#687878]">
              <span className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-[#6A9B5E]" />
                {job.location || "Việt Nam"}
              </span>
              <span className="flex items-center gap-1.5">
                <Banknote className="h-3.5 w-3.5 text-[#6A9B5E]" />
                {job.salary || "Thương lượng"}
              </span>
              <span className="flex items-center gap-1.5">
                <CalendarDays className="h-3.5 w-3.5 text-[#6A9B5E]" />
                {job.postedText || "Mới đăng"}
              </span>
              <span className="flex items-center gap-1.5">
                <UserRound className="h-3.5 w-3.5 text-[#6A9B5E]" />
                {job.level && job.level !== "unknown" ? job.level : "Chưa rõ"}
              </span>
            </div>
          </div>

          <section className="mt-7">
            <h3 className="mb-3 text-sm font-extrabold uppercase tracking-wide text-[#2F4F4F]">
              Lý do phù hợp
            </h3>
            {job.matchReasons.length > 0 ? (
              job.matchReasons.map((reason) => (
                <div
                  key={reason}
                  className="mb-2 flex items-start gap-2 rounded-xl bg-[#f3f8f1] p-3 text-sm text-[#4c6360]"
                >
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#6A9B5E]" />
                  <span>{reason}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-[#71807b]">Chưa có giải thích chi tiết từ hệ thống.</p>
            )}
          </section>

          {job.missingSkills.length > 0 && (
            <section className="mt-6">
              <h3 className="mb-3 text-sm font-extrabold uppercase tracking-wide text-[#2F4F4F]">
                Kỹ năng cần lưu ý
              </h3>
              {job.missingSkills.map((skill) => (
                <div
                  key={skill}
                  className="mb-2 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700"
                >
                  <AlertCircle className="h-4 w-4" />
                  <span>{skill}</span>
                </div>
              ))}
              <p className="mt-2 text-xs italic text-[#82908d]">
                Chỉ bổ sung vào CV nếu bạn thực sự có kỹ năng này.
              </p>
            </section>
          )}

          <section className="mt-6">
            <h3 className="mb-2 text-sm font-extrabold uppercase tracking-wide text-[#2F4F4F]">
              Mô tả công việc
            </h3>
            <p className="whitespace-pre-wrap text-sm leading-6 text-[#657572]">
              {job.descriptionSnippet || "Nguồn tuyển dụng không cung cấp mô tả chi tiết."}
            </p>
          </section>
        </div>

        <div className="space-y-2 border-t border-[#edf0eb] bg-white px-5 py-4">
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#6A9B5E] py-3 text-sm font-bold text-white hover:bg-[#588a50]"
          >
            <span>Ứng tuyển ngay</span>
            <ExternalLink className="h-4 w-4" />
          </a>
          <button
            type="button"
            onClick={() => onFullScan(job)}
            className="w-full rounded-xl border border-[#6A9B5E] py-2.5 text-sm font-bold text-[#5c8e55] hover:bg-[#f2f8f0]"
          >
            Phân tích AI đầy đủ
          </button>
          <button
            type="button"
            onClick={() => onGenerateLetter(job)}
            className="flex w-full items-center justify-center gap-2 rounded-xl py-2 text-sm font-bold text-[#667672] hover:bg-[#f4f6f3]"
          >
            <Mail className="h-4 w-4" />
            <span>Viết thư ứng tuyển</span>
          </button>
        </div>
      </aside>
    </>
  );
}

function CoverLetterPanel({
  job,
  letter,
  isGenerating,
  onClose,
}: {
  job: RankedJobResult;
  letter: GeneratedLetter;
  isGenerating: boolean;
  onClose: () => void;
}) {
  const copyLetter = async () => {
    if (!letter) return;
    await navigator.clipboard.writeText(letter.content);
    toast.success("Đã sao chép nội dung thư.");
  };

  return (
    <>
      <button
        type="button"
        aria-label="Đóng thư ứng tuyển"
        onClick={onClose}
        className="fixed inset-0 z-50 cursor-default bg-black/20"
      />
      <aside
        className="fixed right-0 top-0 z-60 flex h-full w-full max-w-[520px] flex-col rounded-l-2xl bg-white shadow-2xl"
        aria-label="Thư ứng tuyển"
      >
        <div className="flex items-center gap-3 border-b border-[#edf0eb] px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-[#617070] hover:bg-[#f2f6f0]"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
          <div>
            <h2 className="text-lg font-extrabold text-[#2F4F4F]">Thư ứng tuyển AI</h2>
            <p className="text-xs text-[#71807b]">
              {job.title} · {job.company || "Không rõ công ty"}
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6">
          {isGenerating && (
            <div className="flex min-h-64 flex-col items-center justify-center text-center">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#d8ecd4] border-t-[#6A9B5E]" />
              <p className="mt-4 text-sm font-semibold text-[#60706c]">
                Đang phân tích CV và soạn thư ứng tuyển...
              </p>
            </div>
          )}

          {!isGenerating && letter && (
            <div className="space-y-5">
              <div>
                <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-[#74817d]">
                  Tiêu đề thư
                </p>
                <div className="rounded-xl bg-[#f5f7f3] px-4 py-3 text-sm font-semibold text-[#2F4F4F]">
                  {letter.subject}
                </div>
              </div>
              <div>
                <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-[#74817d]">
                  Nội dung thư
                </p>
                <div className="whitespace-pre-wrap rounded-xl bg-[#f5f7f3] px-4 py-4 text-sm leading-6 text-[#536763]">
                  {letter.content}
                </div>
              </div>
            </div>
          )}
        </div>

        {!isGenerating && letter && (
          <div className="border-t border-[#edf0eb] bg-white px-5 py-4">
            <button
              type="button"
              onClick={() => void copyLetter()}
              className="w-full rounded-xl bg-[#6A9B5E] py-3 text-sm font-bold text-white hover:bg-[#588a50]"
            >
              Sao chép nội dung
            </button>
          </div>
        )}
      </aside>
    </>
  );
}

function JobCard({
  job,
  isStretch = false,
  onOpenDetails,
  onGenerateLetter,
  onFullScan,
}: {
  job: RankedJobResult;
  isStretch?: boolean;
  onOpenDetails: () => void;
  onGenerateLetter: () => void;
  onFullScan: () => void;
}) {
  const handleButton = (event: React.MouseEvent, action: () => void) => {
    event.stopPropagation();
    action();
  };

  return (
    <article
      onClick={onOpenDetails}
      className={`mb-4 cursor-pointer rounded-2xl bg-white p-5 shadow-sm transition hover:shadow-md ${
        isStretch ? "border border-dashed border-[#dfe5df]" : ""
      }`}
    >
      <div className="flex flex-wrap items-start gap-3">
        <span className={`rounded-xl px-3 py-1 text-sm font-black text-white ${scoreClass(job.matchScore)}`}>
          {job.matchScore}%
        </span>
        <CompanyLogo
          company={job.company}
          logoUrl={job.companyLogoUrl}
          className="h-10 w-10 shrink-0 rounded-xl"
        />
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-extrabold text-[#2F4F4F]">{job.title}</h3>
          <p className="mt-0.5 text-sm text-[#71807b]">
            {job.company || "Không rõ công ty"}
            <span className="ml-1 rounded-full bg-[#f0f3ef] px-2 py-0.5 text-[10px]">
              {job.source}
            </span>
          </p>
        </div>
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          onClick={(event) => event.stopPropagation()}
          className="rounded-lg p-2 text-[#83908c] hover:bg-[#f3f7f1]"
          aria-label={`Mở ${job.title}`}
        >
          <ExternalLink className="h-5 w-5" />
        </a>
      </div>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-[#71817c]">
        <span className="flex items-center gap-1">
          <MapPin className="h-3.5 w-3.5" />
          {job.location || "Việt Nam"}
        </span>
        <span className="flex items-center gap-1">
          <Banknote className="h-3.5 w-3.5" />
          {job.salary || "Thương lượng"}
        </span>
        <span className="flex items-center gap-1">
          <CalendarDays className="h-3.5 w-3.5" />
          {job.postedText || "Mới đăng"}
        </span>
        {job.level && job.level !== "unknown" && (
          <span className="rounded-full bg-[#f0f3ef] px-2 py-0.5 text-[11px] font-medium">
            {job.level}
          </span>
        )}
      </div>

      {(job.skills.length > 0 || job.missingSkills.length > 0) && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {matchedSkills(job).slice(0, 5).map((skill) => (
            <span
              key={skill}
              className="rounded-full border border-green-200 bg-green-50 px-2 py-1 text-[11px] font-semibold text-green-700"
            >
              {skill}
            </span>
          ))}
          {job.missingSkills.slice(0, 3).map((skill) => (
            <span
              key={skill}
              className="flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2 py-1 text-[11px] font-semibold text-red-600"
            >
              <AlertCircle className="h-3 w-3" />
              {skill}
            </span>
          ))}
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-[#f0f2ef] pt-4">
        <button
          type="button"
          onClick={(event) => handleButton(event, onOpenDetails)}
          className="rounded-lg px-2 py-1.5 text-xs font-bold text-[#667772] hover:bg-[#f3f6f2]"
        >
          Xem chi tiết
        </button>
        <button
          type="button"
          onClick={(event) => handleButton(event, onGenerateLetter)}
          className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-bold text-[#667772] hover:bg-[#f3f6f2]"
        >
          <Mail className="h-3.5 w-3.5" />
          Viết thư ứng tuyển
        </button>
        <button
          type="button"
          onClick={(event) => handleButton(event, onFullScan)}
          className="flex items-center gap-1 rounded-lg border border-[#6A9B5E] bg-[#edf8ea] px-3 py-1.5 text-xs font-extrabold text-[#477d43] shadow-sm hover:bg-[#e1f2dd]"
        >
          <Zap className="h-3.5 w-3.5" />
          Phân tích AI
        </button>
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          onClick={(event) => event.stopPropagation()}
          className="ml-auto flex items-center gap-1 rounded-lg bg-[#6A9B5E] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#588a50]"
        >
          <span>Ứng tuyển</span>
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
    </article>
  );
}

export function JobScanPage({
  profile,
  jobs,
  sourceStatuses,
  queries,
  isLoading,
  loadingStep,
  error,
  targetRole,
  location,
  dateRange,
  selectedSources,
  showStretch,
  selectedJobForLetter,
  generatedLetter,
  isGeneratingLetter,
  onTargetRoleChange,
  onLocationChange,
  onDateRangeChange,
  onSourceToggle,
  onShowStretchChange,
  onSearch,
  onGenerateLetter,
  onFullScan,
  onCloseLetter,
}: JobScanPageProps) {
  const [selectedJob, setSelectedJob] = useState<RankedJobResult | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>("match");
  const [visibleGoodCount, setVisibleGoodCount] = useState(8);

  const sortedJobs = useMemo(() => {
    const result = [...jobs];
    if (sortMode === "newest") {
      return result.sort((a, b) => postedAge(a.postedText) - postedAge(b.postedText));
    }
    if (sortMode === "salary") {
      return result.sort((a, b) => salaryValue(b.salary) - salaryValue(a.salary));
    }
    return result.sort((a, b) => b.matchScore - a.matchScore);
  }, [jobs, sortMode]);

  const goodMatches = sortedJobs.filter((job) => job.matchLabel === "good_match");
  const stretchMatches = sortedJobs.filter((job) => job.matchLabel === "stretch");
  const visibleGoodMatches = goodMatches.slice(0, visibleGoodCount);
  const remainingGoodMatches = Math.max(goodMatches.length - visibleGoodMatches.length, 0);

  return (
    <div className="min-h-full font-sans text-[#2F4F4F]">
      <main className="mx-auto px-1 py-4 sm:px-3 lg:px-6">
        <div className="mb-7 flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div className="flex items-start gap-3">
            <Radar className="mt-1 h-9 w-9 text-[#6A9B5E]" />
            <div>
              <h1 className="text-3xl font-black tracking-tight text-[#2F4F4F]">Quét Việc Làm</h1>
              <p className="mt-1 text-sm text-[#72817d]">
                Tìm việc phù hợp từ CV của bạn trên các nền tảng Việt Nam.
              </p>
            </div>
          </div>
          <div className="flex flex-col items-start gap-1 md:items-end">
            <button
              type="button"
              onClick={onSearch}
              disabled={isLoading || selectedSources.length === 0}
              className="flex items-center gap-2 rounded-xl bg-[#6A9B5E] px-4 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-[#588a50] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              <span>{isLoading ? "Đang quét..." : "Quét việc làm mới"}</span>
            </button>
            <span className="text-xs text-[#87928e]">
              1 tín dụng mỗi lần quét · Hoàn tiền nếu thất bại
            </span>
          </div>
        </div>

        <div className="grid items-start gap-6 lg:grid-cols-[minmax(270px,28%)_1fr]">
          <aside className="space-y-4 lg:sticky lg:top-5">
            <section className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <CircleUserRound className="h-5 w-5 text-[#6A9B5E]" />
                  <span className="text-xs font-extrabold tracking-widest text-[#73807c]">
                    HỒ SƠ ỨNG VIÊN
                  </span>
                </div>
                <span className="rounded-full bg-green-100 px-2 py-1 text-[10px] font-bold text-green-700">
                  Từ CV của bạn
                </span>
              </div>

              <dl className="mt-5 space-y-3 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-[#7a8783]">Vị trí mục tiêu</dt>
                  <dd className="text-right font-bold">
                    {targetRole || profile?.targetRoles?.[0] || "Chưa xác định"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-[#7a8783]">Cấp bậc</dt>
                  <dd>
                    <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-bold capitalize text-amber-700">
                      {profile?.seniority || "unknown"}
                    </span>
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-[#7a8783]">Kinh nghiệm</dt>
                  <dd className="font-semibold">
                    {profile?.yearsOfExperience != null
                      ? `${profile.yearsOfExperience} năm`
                      : "Chưa xác định"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-[#7a8783]">Địa điểm</dt>
                  <dd className="text-right font-semibold">
                    {profile?.location || location || "Tất cả"}
                  </dd>
                </div>
              </dl>

              {profile?.skills && profile.skills.length > 0 && (
                <div className="mt-5">
                  <p className="mb-2 text-xs font-bold uppercase tracking-wider text-[#74817d]">
                    Kỹ năng
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.skills.slice(0, 12).map((skill) => (
                      <span
                        key={skill}
                        className="rounded-full bg-green-50 px-2 py-1 text-[11px] font-medium text-green-800"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                  {profile.skills.length > 12 && (
                    <p className="mt-2 text-xs text-[#87938f]">
                      +{profile.skills.length - 12} kỹ năng khác
                    </p>
                  )}
                </div>
              )}

              {queries.length > 0 && (
                <details className="mt-4 text-xs text-[#71807b]">
                  <summary className="cursor-pointer font-semibold">Từ khóa hệ thống sử dụng</summary>
                  <div className="mt-2 space-y-1">
                    {queries.map((query) => (
                      <p key={query}>“{query}”</p>
                    ))}
                  </div>
                </details>
              )}

              <div className="mt-4 flex gap-2 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">
                <Zap className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Điểm phù hợp ban đầu là ước tính nhanh dựa trên vị trí, kỹ năng, cấp bậc và
                  địa điểm. Phân tích đầy đủ có trong Phân tích AI.
                </span>
              </div>
            </section>

            <section className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-5 w-5 text-[#6A9B5E]" />
                <span className="text-xs font-extrabold tracking-widest text-[#73807c]">
                  TÙY CHỈNH TÌM KIẾM
                </span>
              </div>

              <label className="mt-5 block text-xs font-semibold text-[#6e7c78]">
                Từ khóa
                <input
                  value={targetRole}
                  onChange={(event) => onTargetRoleChange(event.target.value)}
                  placeholder="Ví dụ: Frontend Developer"
                  className="mt-1.5 w-full rounded-xl border border-[#dfe8dc] px-3 py-2.5 text-sm text-[#2F4F4F] outline-none focus:border-[#6A9B5E]"
                />
              </label>

              <label className="mt-3 block text-xs font-semibold text-[#6e7c78]">
                Địa điểm
                <select
                  value={location}
                  onChange={(event) => onLocationChange(event.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-[#dfe8dc] bg-white px-3 py-2.5 text-sm text-[#2F4F4F] outline-none"
                >
                  <option value="Tất cả">Tất cả địa điểm</option>
                  <option value="Hồ Chí Minh">Hồ Chí Minh</option>
                  <option value="Hà Nội">Hà Nội</option>
                  <option value="Đà Nẵng">Đà Nẵng</option>
                  <option value="Remote">Remote</option>
                </select>
              </label>

              <label className="mt-3 block text-xs font-semibold text-[#6e7c78]">
                Thời gian đăng
                <span className="ml-1 inline-flex align-middle" title="Lọc theo thời gian tin đăng">
                  <Info className="h-3 w-3" />
                </span>
                <select
                  value={dateRange}
                  onChange={(event) => onDateRangeChange(event.target.value as DateRangeFilter)}
                  className="mt-1.5 w-full rounded-xl border border-[#dfe8dc] bg-white px-3 py-2.5 text-sm text-[#2F4F4F] outline-none"
                >
                  <option value="1d">24 giờ qua</option>
                  <option value="3d">3 ngày qua</option>
                  <option value="7d">7 ngày qua</option>
                  <option value="14d">14 ngày qua</option>
                  <option value="30d">30 ngày qua</option>
                </select>
              </label>
              <p className="mt-2 text-xs italic text-[#8a9691]">
                Bộ lọc ngày đăng đang được cải thiện.
              </p>

              <label className="mt-4 flex cursor-pointer items-center justify-between gap-3 text-sm text-[#566b67]">
                <span>Bao gồm việc làm Stretch 50–69%</span>
                <input
                  type="checkbox"
                  checked={showStretch}
                  onChange={(event) => onShowStretchChange(event.target.checked)}
                  className="peer sr-only"
                />
                <span
                  className={`relative h-6 w-11 shrink-0 rounded-full transition ${showStretch ? "bg-[#6A9B5E]" : "bg-[#ccd5cf]"}`}
                >
                  <span
                    className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition ${showStretch ? "left-6" : "left-1"}`}
                  />
                </span>
              </label>

              <button
                type="button"
                onClick={onSearch}
                disabled={isLoading || selectedSources.length === 0}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[#6A9B5E] py-2.5 text-sm font-bold text-white hover:bg-[#588a50] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Search className="h-4 w-4" />
                <span>Áp dụng và Quét lại</span>
              </button>
            </section>

            <section className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <Globe2 className="h-5 w-5 text-[#6A9B5E]" />
                <span className="text-xs font-extrabold tracking-widest text-[#73807c]">
                  NGUỒN TÌM VIỆC
                </span>
              </div>
              <ul className="mt-4 space-y-3">
                {SOURCE_OPTIONS.map((source) => {
                  const checked = selectedSources.includes(source.id);
                  const status = sourceStatuses.find((item) => item.source === source.id);
                  let statusText = checked ? "Chưa quét" : "Tắt";
                  let statusClass = "bg-gray-100 text-gray-500";

                  if (checked && isLoading) {
                    statusText = "Đợi kết quả";
                  } else if (checked && status?.status === "success") {
                    statusText = `${status.count} việc`;
                    statusClass = "bg-green-100 text-green-700";
                  } else if (checked && status?.status === "empty") {
                    statusText = "Không có kết quả";
                  } else if (checked && status?.status === "timeout") {
                    statusText = "Hết thời gian";
                    statusClass = "bg-amber-100 text-amber-700";
                  } else if (checked && status?.status === "failed") {
                    statusText = "Thất bại";
                    statusClass = "bg-red-100 text-red-700";
                  }

                  return (
                    <li key={source.id} className="flex items-center gap-2 text-sm">
                      <button
                        type="button"
                        onClick={() => onSourceToggle(source.id)}
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                          checked
                            ? "border-[#6A9B5E] bg-[#6A9B5E] text-white"
                            : "border-[#cbd4ce]"
                        }`}
                        aria-label={`${checked ? "Tắt" : "Bật"} nguồn ${source.name}`}
                      >
                        {checked && <Check className="h-3 w-3" />}
                      </button>
                      <span className="min-w-0 flex-1 truncate text-[#546663]">{source.name}</span>
                      <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-bold ${statusClass}`}>
                        {statusText}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          </aside>

          <section className="min-w-0">
            <div className="mb-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-xl font-black">Kết Quả Quét</h2>
                <p className="mt-1 text-sm text-[#7b8985]">
                  {isLoading ? "Đang cập nhật kết quả..." : `${jobs.length} việc làm · Cập nhật vừa xong`}
                </p>
              </div>
              <select
                value={sortMode}
                onChange={(event) => setSortMode(event.target.value as SortMode)}
                disabled={isLoading}
                className="rounded-xl border border-[#dfe8dc] bg-white px-3 py-2 text-sm text-[#596c67] outline-none"
                aria-label="Sắp xếp kết quả"
              >
                <option value="match">Sắp xếp: Độ phù hợp</option>
                <option value="newest">Mới nhất</option>
                <option value="salary">Mức lương cao nhất</option>
              </select>
            </div>

            {isLoading && (
              <div
                className="flex min-h-[420px] items-center justify-center rounded-2xl bg-white px-6 py-12 text-center shadow-sm"
                role="status"
                aria-live="polite"
              >
                <div className="max-w-sm">
                  <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-[#d8ecd4] border-t-[#6A9B5E]" />
                  <h3 className="mt-4 text-lg font-extrabold">Đang quét việc làm</h3>
                  <p className="mt-2 min-h-10 text-sm text-[#71807b]">{loadingStep}</p>
                </div>
              </div>
            )}

            {error && !isLoading && (
              <div className="rounded-2xl border border-red-100 bg-white p-8 text-center shadow-sm">
                <AlertCircle className="mx-auto h-9 w-9 text-red-500" />
                <h3 className="mt-3 font-extrabold">Không thể quét việc làm</h3>
                <p className="mx-auto mt-1 max-w-md text-sm text-[#71807b]">{error}</p>
                <button
                  type="button"
                  onClick={onSearch}
                  className="mt-4 rounded-xl bg-[#6A9B5E] px-4 py-2 text-sm font-bold text-white"
                >
                  Thử lại
                </button>
              </div>
            )}

            {!error && !isLoading && jobs.length === 0 && (
              <div className="rounded-2xl bg-white p-10 text-center shadow-sm">
                <Search className="mx-auto h-10 w-10 text-[#9aa59f]" />
                <h3 className="mt-3 font-extrabold">Không tìm thấy công việc phù hợp</h3>
                <p className="mx-auto mt-1 max-w-md text-sm text-[#71807b]">
                  Hãy thử đổi vị trí mục tiêu, địa điểm hoặc nguồn tìm việc rồi quét lại.
                </p>
              </div>
            )}

            {!error && !isLoading && goodMatches.length > 0 && (
              <>
                <div className="mb-4 flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-[#6A9B5E]" />
                  <h3 className="text-sm font-black tracking-wide">PHÙ HỢP TỐT NHẤT</h3>
                  <span className="rounded-full bg-green-100 px-2 py-1 text-xs font-bold text-green-700">
                    {goodMatches.length} việc
                  </span>
                  <ChevronDown className="ml-auto h-4 w-4 text-[#82908b]" />
                </div>
                {visibleGoodMatches.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onOpenDetails={() => setSelectedJob(job)}
                    onGenerateLetter={() => onGenerateLetter(job)}
                    onFullScan={() => onFullScan(job)}
                  />
                ))}
                {remainingGoodMatches > 0 && (
                  <button
                    type="button"
                    onClick={() => setVisibleGoodCount((count) => count + 8)}
                    className="mb-9 text-sm font-bold text-[#6A9B5E] hover:underline"
                  >
                    Xem thêm {Math.min(remainingGoodMatches, 8)} việc phù hợp tốt nhất →
                  </button>
                )}
              </>
            )}

            {!error && !isLoading && showStretch && stretchMatches.length > 0 && (
              <>
                <div className="mb-4 mt-8 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-amber-500" />
                  <h3 className="text-sm font-black tracking-wide">VIỆC LÀM STRETCH</h3>
                  <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-bold text-amber-700">
                    {stretchMatches.length} việc
                  </span>
                  <span className="hidden text-xs text-[#88938f] sm:inline">Phù hợp 50–69%</span>
                  <ChevronDown className="ml-auto h-4 w-4 text-[#82908b]" />
                </div>
                {stretchMatches.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    isStretch
                    onOpenDetails={() => setSelectedJob(job)}
                    onGenerateLetter={() => onGenerateLetter(job)}
                    onFullScan={() => onFullScan(job)}
                  />
                ))}
              </>
            )}
          </section>
        </div>
      </main>

      {selectedJob && (
        <DetailPanel
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onFullScan={onFullScan}
          onGenerateLetter={onGenerateLetter}
        />
      )}

      {selectedJobForLetter && (
        <CoverLetterPanel
          job={selectedJobForLetter}
          letter={generatedLetter}
          isGenerating={isGeneratingLetter}
          onClose={onCloseLetter}
        />
      )}
    </div>
  );
}
