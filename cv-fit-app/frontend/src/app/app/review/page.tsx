"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlignLeft,
  ArrowLeft,
  Award,
  BookOpen,
  Briefcase,
  Check,
  ChevronDown,
  Cpu,
  FileText,
  FolderGit2,
  GraduationCap,
  Heart,
  Languages,
  Loader2,
  Minus,
  Plus,
  RotateCcw,
  Save,
  SlidersHorizontal,
  Sparkles,
  Trophy,
  Type,
  User,
  Users,
  StickyNote,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useWorkspace } from "@/context/WorkspaceContext";
import { useAuth } from "@/context/AuthContext";

import {
  getStructuredDocumentAPI,
  mintSourceTicketAPI,
  prefillCVAPI,
  saveStructuredDocumentAPI,
} from "@/lib/api";
import { apiErrorMessage, connectivityMessage } from "@/lib/errorMessages";
import { applyBlockPatch, cloneDocument, dropEmptySummary, isSuppressedCustomSection } from "@/lib/cv-edit-utils";
import { getCachedStructuredDoc, setCachedStructuredDoc } from "@/lib/document-cache";
import { storeWizardHandoff } from "@/lib/wizard-handoff";
import type { CVBlock, CVDocumentV2, CVDesign } from "@/types";
import type { CVTypographyConfig } from "@/lib/cv-render-html";

import { CV_DESIGNS } from "@/lib/cv-designs";

import IdentityForm from "@/components/workspace/IdentityForm";
import LocalCVPreview from "@/components/workspace/LocalCVPreview";
import SectionEditor from "@/components/workspace/SectionEditor";
import SummaryEditor from "@/components/workspace/SummaryEditor";
import FeatureChooserModal, { type FeatureKind } from "@/components/workspace/FeatureChooserModal";
import ReviewSkeleton from "@/components/workspace/ReviewSkeleton";

const CONTACT_MISSING_NOTE =
  "Chưa có thông tin này trong CV gốc — bạn điền vào đây, không phải dữ liệu được trích xuất.";

function isMissingContact(identity: CVDocumentV2["identity"], key: "email" | "phone") {
  const value = (identity as unknown as Record<string, string | string[] | null | undefined>)[key];
  return !value || !String(value).trim();
}

type ResolvedSectionCategory =
  | "contact"
  | "skills"
  | "education"
  | "experience"
  | "projects"
  | "publications"
  | "certifications"
  | "languages"
  | "awards"
  | "activities"
  | "interests"
  | "custom"
  | "summary"
  | "other";

function resolveSectionCategory(type: string, label: string): ResolvedSectionCategory {
  const t = (type || "").toLowerCase();
  const l = (label || "").toLowerCase();
  if (t === "contact" || l.includes("liên hệ") || l.includes("contact")) return "contact";
  if (t === "skills" || l.includes("kỹ năng") || l.includes("skill")) return "skills";
  if (t === "education" || l.includes("học vấn") || l.includes("education")) return "education";
  if (t === "experience" || l.includes("kinh nghiệm") || l.includes("experience")) return "experience";
  if (t === "projects" || l.includes("dự án") || l.includes("nghiên cứu") || l.includes("project")) return "projects";
  if (t === "publications" || l.includes("ấn phẩm") || l.includes("bài báo") || l.includes("pub")) return "publications";
  if (t === "certifications" || l.includes("chứng chỉ") || l.includes("certif")) return "certifications";
  if (t === "languages" || l.includes("ngôn ngữ") || l.includes("ngoại ngữ") || l.includes("language")) return "languages";
  if (t === "awards" || l.includes("giải thưởng") || l.includes("danh hiệu") || l.includes("award") || l.includes("honor")) return "awards";
  if (t === "activities" || l.includes("hoạt động") || l.includes("activit") || l.includes("leadership") || l.includes("lãnh đạo")) return "activities";
  if (t === "interests" || l.includes("sở thích") || l.includes("interest")) return "interests";
  if (t === "custom" || l.includes("bổ sung") || l.includes("additional") || l.includes("other") || l.includes("thông tin")) return "custom";
  if (t === "summary" || l.includes("tóm tắt") || l.includes("summary")) return "summary";
  return "other";
}

const SECTION_METADATA: Record<
  ResolvedSectionCategory,
  { icon: LucideIcon; subtitle: string; defaultLabel: string }
> = {
  contact: { icon: User, subtitle: "Các thông tin cơ bản từ CV của bạn", defaultLabel: "Thông tin liên hệ" },
  skills: { icon: Cpu, subtitle: "Kỹ năng chuyên môn và công cụ từ CV", defaultLabel: "Kỹ năng" },
  education: { icon: GraduationCap, subtitle: "Quá trình đào tạo và bằng cấp học vấn", defaultLabel: "Học vấn" },
  experience: { icon: Briefcase, subtitle: "Kinh nghiệm làm việc và các vị trí đảm nhiệm", defaultLabel: "Kinh nghiệm" },
  projects: { icon: FolderGit2, subtitle: "Các dự án và công trình tiêu biểu", defaultLabel: "Dự án & Nghiên cứu" },
  publications: { icon: BookOpen, subtitle: "Bài báo khoa học và công trình đã xuất bản", defaultLabel: "Ấn phẩm" },
  certifications: { icon: Award, subtitle: "Chứng chỉ chuyên môn và đào tạo", defaultLabel: "Chứng chỉ" },
  languages: { icon: Languages, subtitle: "Ngoại ngữ và trình độ sử dụng", defaultLabel: "Ngoại ngữ" },
  awards: { icon: Trophy, subtitle: "Giải thưởng và danh hiệu đã đạt được", defaultLabel: "Giải thưởng" },
  activities: { icon: Users, subtitle: "Hoạt động ngoại khóa và vai trò lãnh đạo", defaultLabel: "Hoạt động" },
  interests: { icon: Heart, subtitle: "Sở thích cá nhân bổ sung", defaultLabel: "Sở thích" },
  custom: { icon: StickyNote, subtitle: "Thông tin bổ sung chưa được phân loại", defaultLabel: "Thông tin bổ sung" },
  summary: { icon: AlignLeft, subtitle: "Giới thiệu tóm tắt mục tiêu và bản thân", defaultLabel: "Tóm tắt" },
  other: { icon: FileText, subtitle: "Chỉnh sửa nội dung cho mục này", defaultLabel: "Mục khác" },
};

function getSectionMeta(type: string, label: string) {
  return SECTION_METADATA[resolveSectionCategory(type, label)];
}

interface SpacingControlRowProps {
  label: string;
  value: number;
  unit?: string;
  min: number;
  max: number;
  step: number;
  precision?: number;
  displayFormat?: (v: number) => string;
  onChange: (value: number) => void;
}

function SpacingControlRow({
  label,
  value,
  unit = "",
  min,
  max,
  step,
  precision = 1,
  displayFormat,
  onChange,
}: SpacingControlRowProps) {
  const displayVal = displayFormat ? displayFormat(value) : `${value.toFixed(precision)} ${unit}`.trim();
  const handleStep = (direction: -1 | 1) => {
    const next = Math.min(max, Math.max(min, +(value + direction * step).toFixed(precision)));
    onChange(next);
  };

  return (
    <div>
      <div className="flex items-center justify-between text-xs font-medium text-slate-700 mb-1">
        <span>{label}</span>
        <span className="font-semibold text-slate-900">{displayVal}</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1 accent-[#2D7A58] cursor-pointer h-1.5 bg-gray-200 rounded-lg appearance-none"
        />
        <div className="flex items-center rounded-lg border border-gray-200 bg-gray-50 p-0.5">
          <button
            type="button"
            onClick={() => handleStep(-1)}
            disabled={value <= min}
            className="h-5 w-5 flex items-center justify-center rounded text-slate-600 hover:bg-white disabled:opacity-40 cursor-pointer"
            aria-label={`Giảm ${label}`}
          >
            <Minus size={11} />
          </button>
          <button
            type="button"
            onClick={() => handleStep(1)}
            disabled={value >= max}
            className="h-5 w-5 flex items-center justify-center rounded text-slate-600 hover:bg-white disabled:opacity-40 cursor-pointer"
            aria-label={`Tăng ${label}`}
          >
            <Plus size={11} />
          </button>
        </div>
      </div>
    </div>
  );
}

interface DraftState {
  document: CVDocumentV2 | null;
  isPrefilling: boolean;
  prefillError: string | null;
  design: CVDesign;
  savedAt: string | null;
  isSaving: boolean;
  isAnalyzing: boolean;
  snapshot: string | null;
  snapshotDirty: boolean;
}

export default function ReviewPage() {
  const router = useRouter();
  const {
    cvText,
    cvFileName,
    jdText,
    rawExtractionRef,
    selectedCvId,
    isLoaded,
    clearCache,
    updateWorkspace,
  } = useWorkspace();
  const { userId } = useAuth();

  const [activeTab, setActiveTab] = useState<string>("contact");
  const loadedCvIdRef = useRef<string | null>(null);

  const [state, setState] = useState<DraftState>({
    document: null,
    isPrefilling: true,
    prefillError: null,
    design: "classic_ats",
    savedAt: null,
    isSaving: false,
    isAnalyzing: false,
    snapshot: null,
    snapshotDirty: false,
  });

  type ConcreteTypographyConfig = Omit<Required<CVTypographyConfig>, "fontSize" | "lineHeight"> & {
    lineHeight: number;
  };

  const DEFAULT_TYPOGRAPHY: ConcreteTypographyConfig = {
    fontFamily: "'Times New Roman'",
    baseFontSize: 9.5,
    lineHeight: 1.4,
    sectionSpacing: 4.0,
    itemSpacing: 3.0,
    pageMargin: 12,
  };

  const [typography, setTypography] = useState<ConcreteTypographyConfig>(DEFAULT_TYPOGRAPHY);
  const [showSpacingPopover, setShowSpacingPopover] = useState(false);
  const spacingPopoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        spacingPopoverRef.current &&
        !spacingPopoverRef.current.contains(event.target as Node)
      ) {
        setShowSpacingPopover(false);
      }
    }
    if (showSpacingPopover) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showSpacingPopover]);

  const draft = state.document;
  const tabs = useMemo(() => {
    if (!draft) return [] as { id: string; label: string; type: string }[];
    const list: { id: string; label: string; type: string }[] = [];
    list.push({ id: "contact", label: "Thông tin liên hệ", type: "contact" });
    const seenLabels = new Map<string, number>();
    for (const section of draft.sections) {
      if (isSuppressedCustomSection(section)) continue;
      const label = section.title || getSectionMeta(section.type, section.title || section.type).defaultLabel;
      const count = (seenLabels.get(label) ?? 0) + 1;
      seenLabels.set(label, count);
      const displayLabel = count > 1 ? (section.title || `${label} (${count})`) : label;

      list.push({
        id: section.id,
        label: displayLabel,
        type: section.type,
      });
    }
    list.push({ id: "__summary", label: "Tóm tắt", type: "summary" });
    return list;
  }, [draft]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!selectedCvId || !cvText.trim()) {
      router.replace("/app/setup");
    }
  }, [isLoaded, selectedCvId, cvText, router]);

  useEffect(() => {
    if (!isLoaded || !selectedCvId || !cvText.trim()) return;
    if (loadedCvIdRef.current === selectedCvId && state.document) return;
    let cancelled = false;

    const load = async () => {
      // 1. Instant check in client sessionStorage cache (0ms)
      const cached = getCachedStructuredDoc(selectedCvId, userId);
      if (cached) {
        loadedCvIdRef.current = selectedCvId;
        const cloned = cloneDocument(cached);
        const snapshot = JSON.stringify(cloned);
        setState((s) => ({
          ...s,
          document: cloned,
          isPrefilling: false,
          prefillError: null,
          snapshot,
          snapshotDirty: false,
        }));
        return;
      }

      loadedCvIdRef.current = selectedCvId;

      // 2. Fetch saved structured draft from DB
      try {
        const saved = await getStructuredDocumentAPI(selectedCvId);
        if (cancelled) return;
        if (saved.saved) {
          const cloned = cloneDocument(saved.saved);
          const snapshot = JSON.stringify(cloned);
          setCachedStructuredDoc(selectedCvId, cloned, userId);
          setState((s) => ({
            ...s,
            document: cloned,
            isPrefilling: false,
            prefillError: null,
            snapshot,
            snapshotDirty: false,
          }));
          return;
        }
      } catch {
      }

      // 3. Deterministic prefill with server auto-persist
      try {
        const prefill = await prefillCVAPI(
          cvText,
          rawExtractionRef?.id,
          selectedCvId,
        );
        if (cancelled) return;
        const cloned = cloneDocument(prefill.prefill_document_v2);
        const snapshot = JSON.stringify(cloned);
        setCachedStructuredDoc(selectedCvId, cloned, userId);
        // Ensure background persistence only if backend route skipped it
        if (!prefill.auto_persisted) {
          void saveStructuredDocumentAPI(selectedCvId, cloned).catch((persistErr) => {
            console.warn("Background auto-save of prefill failed:", persistErr);
          });
        }
        setState((s) => ({
          ...s,
          document: cloned,
          isPrefilling: false,
          prefillError: null,
          snapshot,
          snapshotDirty: false,
        }));
      } catch (err) {
        if (cancelled) return;
        setState((s) => ({
          ...s,
          isPrefilling: false,
          prefillError: connectivityMessage(err),
        }));
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, selectedCvId, cvText, rawExtractionRef?.id, userId, state.document]);

  useEffect(() => {
    if (tabs.length > 0 && !tabs.some((t) => t.id === activeTab)) {
      setActiveTab(tabs[0].id);
    }
  }, [tabs, activeTab]);

  useEffect(() => {
    if (!draft || !state.snapshot) return;
    const current = JSON.stringify(draft);
    setState((s) => ({ ...s, snapshotDirty: current !== state.snapshot }));
  }, [draft, state.snapshot]);

  const isTabDirty = (tabId: string): boolean => {
    if (!draft || !state.snapshot) return false;
    try {
      const snapDoc = JSON.parse(state.snapshot) as CVDocumentV2;
      if (tabId === "contact") {
        return JSON.stringify(draft.identity) !== JSON.stringify(snapDoc.identity);
      }
      if (tabId === "__summary") {
        return JSON.stringify(draft.summary) !== JSON.stringify(snapDoc.summary);
      }
      const section = draft.sections.find((s) => s.id === tabId);
      const savedSection = snapDoc.sections.find((s) => s.id === tabId);
      return JSON.stringify(section) !== JSON.stringify(savedSection);
    } catch {
      return false;
    }
  };

  const handleIdentityChange = (patch: Partial<CVDocumentV2["identity"]>) => {
    if (!draft) return;
    setState((s) => {
      if (!s.document) return s;
      return {
        ...s,
        document: {
          ...s.document,
          identity: {
            ...s.document.identity,
            ...patch,
          },
        },
      };
    });
  };

  const handleIdentityHiddenChange = (hiddenFields: string[]) => {
    if (!draft) return;
    setState((s) => {
      if (!s.document) return s;
      return {
        ...s,
        document: {
          ...s.document,
          identity: {
            ...s.document.identity,
            hidden_fields: hiddenFields,
          },
        },
      };
    });
  };

  const handleSummaryChange = (text: string) => {
    if (!draft) return;
    setState((s) => {
      if (!s.document) return s;
      const current = s.document.summary;
      const updated = current
        ? { ...current, text, origin: "user_edit" as const }
        : {
            type: "paragraph" as const,
            block_id: `sum_${Date.now()}`,
            text,
            origin: "user_edit" as const,
          };
      return {
        ...s,
        document: {
          ...s.document,
          summary: updated,
        },
      };
    });
  };

  const handleSummaryToggleHidden = () => {
    if (!draft || !draft.summary) return;
    setState((s) => {
      if (!s.document || !s.document.summary) return s;
      return {
        ...s,
        document: {
          ...s.document,
          summary: {
            ...s.document.summary,
            hidden: !s.document.summary.hidden,
            origin: "user_edit" as const,
          },
        },
      };
    });
  };

  const updateSectionBlocks = (
    sectionId: string,
    updater: (blocks: CVBlock[]) => CVBlock[],
  ) => {
    if (!draft) return;
    setState((s) => {
      if (!s.document) return s;
      return {
        ...s,
        document: {
          ...s.document,
          sections: s.document.sections.map((section) =>
            section.id === sectionId
              ? { ...section, blocks: updater(section.blocks) }
              : section,
          ),
        },
      };
    });
  };

  const handleBlockChange = (sectionId: string, blockId: string, patch: Partial<CVBlock>) => {
    updateSectionBlocks(sectionId, (blocks) =>
      blocks.map((b) => (b.block_id === blockId ? applyBlockPatch(b, patch) : b)),
    );
  };

  const handleAddBlock = (sectionId: string, newBlock: CVBlock) => {
    updateSectionBlocks(sectionId, (blocks) => [...blocks, newBlock]);
  };

  const handleRemoveBlock = (sectionId: string, blockId: string) => {
    updateSectionBlocks(sectionId, (blocks) => blocks.filter((b) => b.block_id !== blockId));
  };

  const handleToggleBlockHidden = (sectionId: string, blockId: string) => {
    updateSectionBlocks(sectionId, (blocks) =>
      blocks.map((b) => (b.block_id === blockId ? { ...b, hidden: !b.hidden } : b)),
    );
  };

  const persistDraft = async (sectionLabel?: string): Promise<boolean> => {
    if (!draft || !selectedCvId || state.isSaving) return false;
    setState((s) => ({ ...s, isSaving: true }));
    try {
      const toSave = dropEmptySummary(draft);
      const res = await saveStructuredDocumentAPI(selectedCvId, toSave);
      setCachedStructuredDoc(selectedCvId, toSave, userId);
      setState((s) => ({
        ...s,
        savedAt: res.updated_at,
        isSaving: false,
        snapshot: JSON.stringify(toSave),
        snapshotDirty: false,
      }));
      if (sectionLabel) {
        toast.success(`Đã lưu "${sectionLabel}" thành công.`);
      } else {
        toast.success("Đã lưu bản sửa CV.");
      }
      return true;
    } catch (err) {
      setState((s) => ({ ...s, isSaving: false }));
      toast.error(apiErrorMessage(err));
      return false;
    }
  };

  const handleSave = () => persistDraft();

  const [showChooser, setShowChooser] = useState(false);

  // Deep link from the CV library action sheet: ?features=1 auto-opens the
  // chooser once the draft is ready (never on garbage — see canUseFeatures).
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("features") === "1") {
      setShowChooser(true);
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  const isReviewValid = (): boolean => {
    if (!draft) return false;
    const hasName = Boolean(
      draft.identity.full_name?.trim() || draft.identity.name?.trim() || cvFileName?.trim(),
    );
    if (!hasName) return false;
    const hasContent =
      Boolean(draft.summary?.text.trim()) ||
      draft.sections.some((s) => s.blocks.length > 0);
    return hasContent;
  };

  const canUseFeatures = Boolean(state.snapshot) && isReviewValid();

  const ensureSavedForFeatures = async (): Promise<boolean> => {
    if (!draft || !selectedCvId) return false;
    if (!isReviewValid()) {
      toast.error("Hãy nhập tên CV và ít nhất một mục nội dung trước khi tiếp tục.");
      return false;
    }
    if (state.snapshotDirty || !state.snapshot) {
      return persistDraft();
    }
    return true;
  };

  const handleSaveAndContinue = async () => {
    const ok = await ensureSavedForFeatures();
    if (ok) setShowChooser(true);
  };

  const handlePickFeature = async (kind: FeatureKind, jd?: string, jdName?: string | null) => {
    if (!draft || !selectedCvId) return;
    if (kind === "interview") {
      setShowChooser(false);
      router.push("/app/interview");
      return;
    }
    if (kind === "jobs") {
      setShowChooser(false);
      router.push("/app/jobs");
      return;
    }
    if (kind === "tailor" && jd !== undefined) {
      // JD collected at pick time — scope it to this run before analysis.
      updateWorkspace({ jdText: jd, jdFileName: jdName ?? null });
    }
    // analyze (no JD) + tailor (JD just synced) both live in /app/analyzer.
    await handleAnalyze();
  };

  const handleSectionSave = (tabId: string) => {
    const tabObj = tabs.find((t) => t.id === tabId);
    return persistDraft(tabObj?.label ?? "mục này");
  };

  const handleAnalyze = async () => {
    if (!draft || !selectedCvId || state.isAnalyzing) return;
    setState((s) => ({ ...s, isAnalyzing: true }));
    try {
      const needsSave = state.snapshotDirty || !state.snapshot;
      if (needsSave) {
        await saveStructuredDocumentAPI(selectedCvId, dropEmptySummary(draft));
      }
      const { saved } = await getStructuredDocumentAPI(selectedCvId);
      if (!saved) throw new Error("Không tải được bản CV vừa lưu.");
      // Explicit review attestation: the candidate has seen the full render
      // and clicked through. Stamped before the source ticket binds this
      // exact document, so the reconstruction gate can honor it for
      // machine-provenance warnings. Set once; never cleared by later edits.
      let attested = saved;
      if (!saved.review_attested) {
        attested = dropEmptySummary({ ...saved, review_attested: true });
        await saveStructuredDocumentAPI(selectedCvId, attested);
        setCachedStructuredDoc(selectedCvId, attested, userId);
      }
      setState((s) => ({ ...s, snapshot: JSON.stringify(attested) }));
      const { source_ticket, canonical_cv } = await mintSourceTicketAPI(
        cvText,
        attested,
        rawExtractionRef?.id,
      );
      storeWizardHandoff(userId, {
        source_document_v2: attested,
        canonical_cv,
        source_ticket,
        source_cv_id: selectedCvId,
        design: state.design,
      });
      clearCache();
      router.push("/app/analyzer?from=review");
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setState((s) => ({ ...s, isAnalyzing: false }));
    }
  };

  if (state.prefillError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center bg-[#FBFBFA]">
        <p className="text-sm font-bold text-[#B22222]">Không thể tải bản nháp CV.</p>
        <p className="text-xs text-gray-500">{state.prefillError}</p>
        <button
          type="button"
          onClick={() => router.push("/app/setup")}
          className="rounded-xl bg-[#2D7A58] px-4 py-2 text-xs font-bold text-white shadow-xs cursor-pointer"
        >
          Quay lại chọn CV
        </button>
      </div>
    );
  }

  if (!isLoaded || !draft) {
    return <ReviewSkeleton cvFileName={cvFileName} />;
  }

  const contactMissingEmail = isMissingContact(draft.identity, "email");
  const contactMissingPhone = isMissingContact(draft.identity, "phone");

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#FBFBFA]">
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 bg-white border-b border-gray-100 shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/app/setup")}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-slate-800 transition-colors"
            title="Quay lại danh sách CV"
            aria-label="Quay lại danh sách CV"
          >
            <ArrowLeft size={17} />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-800 tracking-tight">
              {cvFileName || "CV_NTMDuy.pdf"}
            </span>
            <span
              className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[#EAF5EC] text-[#2D7A58]"
              title={state.snapshotDirty ? "Có thay đổi chưa lưu" : "Đã lưu tự động / Sẵn sàng"}
            >
              <Check size={12} strokeWidth={2.5} />
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-medium">Giao diện:</span>
            <select
              value={state.design}
              onChange={(e) => setState((s) => ({ ...s, design: e.target.value as CVDesign }))}
              className="rounded-xl border border-gray-200/90 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-gray-300 focus:border-[#2D7A58] focus:outline-none focus:ring-2 focus:ring-[#2D7A58]/10"
            >
              {CV_DESIGNS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={handleSave}
            disabled={state.isSaving}
            className={`inline-flex items-center gap-1.5 rounded-xl border px-3.5 py-1.5 text-xs font-semibold shadow-xs transition-all cursor-pointer ${
              state.snapshotDirty
                ? "border-[#2D7A58]/30 bg-[#EAF5EC] text-[#2D7A58] hover:bg-[#d9ede0]"
                : "border-gray-200/90 bg-white text-slate-700 hover:bg-gray-50"
            }`}
          >
            {state.isSaving ? (
              <Loader2 size={13} className="animate-spin text-[#2D7A58]" />
            ) : (
              <Save size={13} className={state.snapshotDirty ? "text-[#2D7A58]" : "text-gray-500"} />
            )}
            Lưu nháp
            {state.snapshotDirty && (
              <span className="h-1.5 w-1.5 rounded-full bg-[#2D7A58]" />
            )}
          </button>

          <button
            type="button"
            onClick={handleSaveAndContinue}
            disabled={state.isAnalyzing || state.isSaving}
            className="inline-flex items-center gap-1.5 rounded-full bg-[#2D7A58] px-4 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-[#246347] disabled:opacity-60 disabled:cursor-not-allowed transition-all"
          >
            {state.isAnalyzing ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                Đang chuẩn bị...
              </>
            ) : (
              <>
                Lưu & Tiếp tục
                <Sparkles size={13} />
              </>
            )}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2.5 px-6 py-2 bg-white border-b border-gray-100 shrink-0">
        {/* Section Selector Dropdown */}
        <div className="relative">
          <select
            value={activeTab}
            onChange={(e) => setActiveTab(e.target.value)}
            className="appearance-none rounded-xl border border-gray-200 bg-white pl-9 pr-8 py-1.5 text-xs font-semibold text-slate-800 hover:border-gray-300 focus:border-[#2D7A58] focus:outline-none cursor-pointer shadow-2xs"
            aria-label="Chọn phần CV để chỉnh sửa"
          >
            {tabs.map((tab) => {
              const dirty = isTabDirty(tab.id);
              return (
                <option key={tab.id} value={tab.id}>
                  {tab.label} {dirty ? "• (Chưa lưu)" : ""}
                </option>
              );
            })}
          </select>
          <div className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#2D7A58]">
            {(() => {
              const currentTab = tabs.find((t) => t.id === activeTab);
              const IconComponent = currentTab ? getSectionMeta(currentTab.type, currentTab.label).icon : User;
              return <IconComponent size={14} />;
            })()}
          </div>
          <ChevronDown size={12} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
        </div>

        {/* Subtle vertical divider */}
        <div className="h-4 w-px bg-gray-200 mx-0.5" />

        {/* Font Family */}
        <div className="relative">
          <select
            value={typography.fontFamily}
            onChange={(e) => setTypography((t) => ({ ...t, fontFamily: e.target.value }))}
            className="appearance-none rounded-xl border border-gray-200 bg-white pl-8 pr-7 py-1.5 text-xs font-medium text-slate-700 hover:border-gray-300 focus:border-[#2D7A58] focus:outline-none cursor-pointer"
            aria-label="Kiểu font chữ"
          >
            <option value="'Times New Roman'">Times New Roman</option>
            <option value="Inter">Inter</option>
            <option value="Roboto">Roboto</option>
            <option value="Georgia">Georgia</option>
            <option value="Merriweather">Merriweather</option>
            <option value="Arial">Arial</option>
          </select>
          <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-500">
            Aa
          </span>
          <ChevronDown size={12} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
        </div>

        {/* Base Font Size Stepper */}
        <div className="inline-flex items-center rounded-xl border border-gray-200 bg-white p-0.5 shadow-2xs">
          <button
            type="button"
            onClick={() =>
              setTypography((t) => ({
                ...t,
                baseFontSize: Math.max(8.0, +(t.baseFontSize - 0.5).toFixed(1)),
              }))
            }
            disabled={typography.baseFontSize <= 8.0}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            title="Giảm cỡ chữ (0.5pt)"
            aria-label="Giảm cỡ chữ"
          >
            <Minus size={13} />
          </button>
          <div className="flex items-center gap-1 px-2 text-xs font-semibold text-slate-700 min-w-[58px] justify-center select-none">
            <Type size={12} className="text-slate-400" />
            <span>{typography.baseFontSize.toFixed(1)} pt</span>
          </div>
          <button
            type="button"
            onClick={() =>
              setTypography((t) => ({
                ...t,
                baseFontSize: Math.min(13.0, +(t.baseFontSize + 0.5).toFixed(1)),
              }))
            }
            disabled={typography.baseFontSize >= 13.0}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            title="Tăng cỡ chữ (0.5pt)"
            aria-label="Tăng cỡ chữ"
          >
            <Plus size={13} />
          </button>
        </div>

        {/* Spacing & Layout Popover */}
        <div className="relative" ref={spacingPopoverRef}>
          <button
            type="button"
            onClick={() => setShowSpacingPopover((v) => !v)}
            className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold shadow-2xs transition-all cursor-pointer ${
              showSpacingPopover
                ? "border-[#2D7A58] bg-[#EBF7EE] text-[#2D7A58]"
                : "border-gray-200 bg-white text-slate-700 hover:border-gray-300 hover:bg-slate-50"
            }`}
            aria-expanded={showSpacingPopover}
            aria-label="Cài đặt giãn cách và bố cục"
          >
            <SlidersHorizontal size={13} />
            <span>Giãn cách</span>
            <ChevronDown
              size={12}
              className={`text-gray-400 transition-transform duration-200 ${
                showSpacingPopover ? "rotate-180 text-[#2D7A58]" : ""
              }`}
            />
          </button>

          {showSpacingPopover && (
            <div className="absolute left-0 top-full mt-2 z-50 w-80 rounded-2xl border border-gray-200 bg-white p-4 shadow-xl">
              {/* Header */}
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-gray-100">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <SlidersHorizontal size={13} className="text-[#2D7A58]" />
                  Bố cục & Khoảng cách
                </span>
                <button
                  type="button"
                  onClick={() => setTypography((t) => ({ ...t, ...DEFAULT_TYPOGRAPHY }))}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-[#2D7A58] transition-colors cursor-pointer"
                  title="Đặt lại thông số mặc định"
                >
                  <RotateCcw size={11} />
                  Mặc định
                </button>
              </div>

              <div className="space-y-3.5">
                <SpacingControlRow
                  label="Khoảng cách phần"
                  value={typography.sectionSpacing}
                  unit="mm"
                  min={0}
                  max={10.0}
                  step={0.5}
                  onChange={(val) => setTypography((t) => ({ ...t, sectionSpacing: val }))}
                />
                <SpacingControlRow
                  label="Khoảng cách mục"
                  value={typography.itemSpacing}
                  unit="mm"
                  min={0}
                  max={8.0}
                  step={0.5}
                  onChange={(val) => setTypography((t) => ({ ...t, itemSpacing: val }))}
                />
                <SpacingControlRow
                  label="Độ giãn dòng"
                  value={typography.lineHeight}
                  unit="x"
                  min={1.0}
                  max={1.80}
                  step={0.05}
                  precision={2}
                  displayFormat={(v) => `${v.toFixed(2)}x`}
                  onChange={(val) => setTypography((t) => ({ ...t, lineHeight: val }))}
                />
                <SpacingControlRow
                  label="Lề trang"
                  value={typography.pageMargin}
                  unit="mm"
                  min={0}
                  max={20}
                  step={1}
                  precision={0}
                  onChange={(val) => setTypography((t) => ({ ...t, pageMargin: val }))}
                />
              </div>

              {/* Pro-tip */}
              <div className="mt-3.5 pt-2.5 border-t border-gray-100 text-[11px] text-slate-500 leading-relaxed bg-[#F8FAF9] -mx-4 -mb-4 p-3 rounded-b-2xl">
                💡 <span className="font-medium text-slate-700">Mẹo:</span> Giảm khoảng cách mục hoặc lề trang nếu CV bị tràn sang trang 2 chỉ một vài dòng.
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[1fr_450px] xl:grid-cols-[1fr_530px] 2xl:grid-cols-[1fr_610px] overflow-hidden">
        <div className="flex min-h-0 flex-col overflow-hidden bg-white border-r border-gray-200">
          <div className="flex-1 overflow-y-auto px-8 py-6 bg-white">
            {tabs.map((tab) => {
              if (tab.id !== activeTab) return null;
              const { icon: TabIcon, subtitle } = getSectionMeta(tab.type, tab.label);
              const tabDirty = isTabDirty(tab.id);

              return (
                <div key={tab.id} className="max-w-3xl mx-auto">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-4 mb-5">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-[#EAF5EC] p-2 text-[#2D7A58]">
                        <TabIcon size={20} />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-800 tracking-tight">
                          {tab.label}
                        </h2>
                        <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {tabDirty && (
                        <span className="text-[11px] text-amber-600 font-medium flex items-center gap-1 mr-1">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                          Chưa lưu
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => handleSectionSave(tab.id)}
                        disabled={state.isSaving}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-[#2D7A58] px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-[#246347] disabled:opacity-50 transition-all cursor-pointer"
                      >
                        {state.isSaving ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <Save size={13} />
                        )}
                        Lưu mục này
                      </button>
                    </div>
                  </div>

                  {tab.type === "contact" && (
                    <div className="space-y-4">
                      {contactMissingEmail && (
                        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-700">
                          Email: {CONTACT_MISSING_NOTE}
                        </p>
                      )}
                      {contactMissingPhone && (
                        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-700">
                          Điện thoại: {CONTACT_MISSING_NOTE}
                        </p>
                      )}
                      <IdentityForm
                        identity={draft.identity}
                        onChange={handleIdentityChange}
                        onHiddenChange={handleIdentityHiddenChange}
                      />
                    </div>
                  )}

                  {tab.type === "summary" && (
                    <SummaryEditor
                      summary={draft.summary}
                      onChange={handleSummaryChange}
                      onToggleHidden={handleSummaryToggleHidden}
                      hidden={!!draft.summary?.hidden}
                    />
                  )}

                  {tab.type !== "contact" && tab.type !== "summary" && (() => {
                    const section = draft.sections.find((s) => s.id === tab.id);
                    if (!section) return null;
                    return (
                      <SectionEditor
                        section={section}
                        onBlockChange={(blockId, patch) =>
                          handleBlockChange(section.id, blockId, patch)
                        }
                        onToggleHidden={(blockId) =>
                          handleToggleBlockHidden(section.id, blockId)
                        }
                        onAddBlock={(block) => handleAddBlock(section.id, block)}
                        onRemoveBlock={(blockId) => handleRemoveBlock(section.id, blockId)}
                      />
                    );
                  })()}

                  <div className="mt-8 pt-4 border-t border-gray-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {tabDirty ? (
                        <span className="text-xs text-amber-600 font-medium flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                          Có thay đổi chưa lưu trong mục này
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 flex items-center gap-1.5">
                          <Check size={14} className="text-[#2D7A58]" />
                          Mục này đã được lưu
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSectionSave(tab.id)}
                      disabled={state.isSaving}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-[#2D7A58] px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-[#246347] disabled:opacity-50 transition-all cursor-pointer"
                    >
                      {state.isSaving ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Save size={14} />
                      )}
                      Lưu thay đổi mục này
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="h-full min-h-0 overflow-hidden">
          <LocalCVPreview
            document={draft}
            design={state.design}
            activeSectionType={tabs.find((t) => t.id === activeTab)?.type ?? null}
            typography={typography}
          />
        </div>
      </div>
      <FeatureChooserModal
        open={showChooser}
        cvName={cvFileName || draft.identity.full_name || "CV"}
        canUseFeatures={canUseFeatures}
        initialJdText={jdText}
        onClose={() => setShowChooser(false)}
        onPick={(kind, jd, jdName) => void handlePickFeature(kind, jd, jdName)}
      />
    </div>
  );
}
