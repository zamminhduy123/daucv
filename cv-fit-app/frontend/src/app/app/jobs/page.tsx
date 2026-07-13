"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  JobScanPage,
  type DateRangeFilter,
} from "@/components/magicpath/job-scan-page-dau/JobScanPage";
import { useAuth } from "@/context/AuthContext";
import { useWorkspace } from "@/context/WorkspaceContext";
import { generateWritingAPI, searchJobsAPI } from "@/lib/api";
import { apiErrorMessage } from "@/lib/errorMessages";
import type {
  CandidateProfile,
  JobSourceStatus,
  RankedJobResult,
} from "@/lib/jobs/types";

const ALL_SOURCES = [
  "itviec",
  "topcv",
  "vietnamworks",
  "ybox",
  "glints",
  "jobsgo",
  "careerviet",
  "vieclam24h",
];

export default function JobsPage() {
  const router = useRouter();
  const { cvText, hasData, isLoaded, updateWorkspace } = useWorkspace();
  const { refreshCredits } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [jobs, setJobs] = useState<RankedJobResult[]>([]);
  const [sourceStatuses, setSourceStatuses] = useState<JobSourceStatus[]>([]);
  const [queries, setQueries] = useState<string[]>([]);

  const [targetRole, setTargetRole] = useState("");
  const [location, setLocation] = useState("Tất cả");
  const [dateRange, setDateRange] = useState<DateRangeFilter>("7d");
  const [selectedSources, setSelectedSources] = useState<string[]>(ALL_SOURCES);
  const [showStretch, setShowStretch] = useState(true);

  const [isGeneratingLetter, setIsGeneratingLetter] = useState(false);
  const [generatedLetter, setGeneratedLetter] = useState<{
    subject: string;
    content: string;
  } | null>(null);
  const [selectedJobForLetter, setSelectedJobForLetter] =
    useState<RankedJobResult | null>(null);

  useEffect(() => {
    if (isLoaded && !hasData) router.replace("/app/setup");
  }, [hasData, isLoaded, router]);

  const handleSearch = useCallback(
    async (isInitial = false) => {
      if (!cvText || isLoading) return;

      setIsLoading(true);
      setError("");
      setSourceStatuses([]);

      const steps = [
        "Đang trích xuất thông tin từ CV của bạn...",
        "Đang tìm việc trên các nguồn đã chọn...",
        "Đang loại bỏ tin trùng và tin đã đóng...",
        "Đang tính toán mức độ phù hợp...",
      ];
      let stepIndex = 0;
      setLoadingStep(steps[stepIndex++]);
      const progressTimer = window.setInterval(() => {
        if (stepIndex < steps.length) setLoadingStep(steps[stepIndex++]);
      }, 1800);

      try {
        const response = await searchJobsAPI({
          cvText,
          targetRole: targetRole || undefined,
          location: location === "Tất cả" ? undefined : location,
          dateRange,
          sources: selectedSources,
        });

        void refreshCredits().catch(() => null);
        setProfile(response.profile);
        setJobs(response.jobs);
        setSourceStatuses(response.sourceStatus);
        setQueries(response.queries || []);

        if (isInitial && response.profile) {
          if (response.profile.targetRoles?.[0]) {
            setTargetRole(response.profile.targetRoles[0]);
          }
          if (response.profile.location) setLocation(response.profile.location);
        }

        toast.success(`Tìm thấy ${response.jobs.length} công việc phù hợp.`);
      } catch (caughtError: unknown) {
        const message = apiErrorMessage(caughtError);
        setError(message);
        toast.error(message);
      } finally {
        window.clearInterval(progressTimer);
        setIsLoading(false);
        setLoadingStep("");
      }
    }, [
      cvText,
      dateRange,
      isLoading,
      location,
      refreshCredits,
      selectedSources,
      targetRole,
    ],
  );

  const isFirstLoad = useRef(true);
  useEffect(() => {
    if (!isLoaded || !hasData || !isFirstLoad.current) return;
    isFirstLoad.current = false;
    void handleSearch(true);
  }, [handleSearch, hasData, isLoaded]);

  const handleSourceToggle = (sourceId: string) => {
    setSelectedSources((current) =>
      current.includes(sourceId)
        ? current.filter((source) => source !== sourceId)
        : [...current, sourceId],
    );
  };

  const handleFullScan = (job: RankedJobResult) => {
    const derivedJd =
      `Vị trí công việc: ${job.title}\n` +
      `Công ty: ${job.company || "Không rõ"}\n` +
      `Địa điểm: ${job.location || "Việt Nam"}\n` +
      `Mức lương: ${job.salary || "Thương lượng"}\n` +
      `Kỹ năng yêu cầu: ${job.skills.join(", ") || "Không yêu cầu chi tiết"}\n\n` +
      `Mô tả sơ lược:\n${job.descriptionSnippet || "Không có mô tả chi tiết từ nguồn tuyển dụng."}`;

    updateWorkspace({ jdText: derivedJd });
    toast.success("Đang chuyển sang Phân tích AI với CV và JD đã chọn.");
    router.push("/app/analyzer");
  };

  const generateCoverLetter = async (job: RankedJobResult) => {
    setIsGeneratingLetter(true);
    setSelectedJobForLetter(job);
    setGeneratedLetter(null);

    try {
      const jdText =
        `Job Title: ${job.title}\n` +
        `Company: ${job.company || "Unknown"}\n` +
        `Description: ${job.descriptionSnippet || "No detailed description was provided by the job source."}\n` +
        `Required Skills: ${job.skills.join(", ")}`;
      const response = await generateWritingAPI({
        cv_text: cvText,
        jd_text: jdText,
        writing_type: "cover_letter",
        tone: "professional",
      });

      setGeneratedLetter({
        subject: response.subject_line || `Thư ứng tuyển - ${job.title}`,
        content: response.content || "",
      });
      toast.success("Đã tạo thư ứng tuyển.");
    } catch (caughtError: unknown) {
      toast.error(apiErrorMessage(caughtError));
      setSelectedJobForLetter(null);
    } finally {
      setIsGeneratingLetter(false);
    }
  };

  if (!isLoaded || !hasData) return null;

  return (
    <JobScanPage
      profile={profile}
      jobs={jobs}
      sourceStatuses={sourceStatuses}
      queries={queries}
      isLoading={isLoading}
      loadingStep={loadingStep}
      error={error}
      targetRole={targetRole}
      location={location}
      dateRange={dateRange}
      selectedSources={selectedSources}
      showStretch={showStretch}
      selectedJobForLetter={selectedJobForLetter}
      generatedLetter={generatedLetter}
      isGeneratingLetter={isGeneratingLetter}
      onTargetRoleChange={setTargetRole}
      onLocationChange={setLocation}
      onDateRangeChange={setDateRange}
      onSourceToggle={handleSourceToggle}
      onShowStretchChange={setShowStretch}
      onSearch={() => void handleSearch(false)}
      onGenerateLetter={(job) => void generateCoverLetter(job)}
      onFullScan={handleFullScan}
      onCloseLetter={() => setSelectedJobForLetter(null)}
    />
  );
}
