import type { CVDesign, CVTemplateDefinition } from "@/types";

export interface CVDesignDefinition {
  value: CVDesign;
  label: string;
  description: string;
}

export const DEFAULT_CV_TEMPLATES: readonly CVDesignDefinition[] = [
  { value: "classic_ats", label: "Classic ATS", description: "Tối ưu ATS, đơn giản, chuẩn mực." },
  { value: "modern_professional", label: "Modern Professional", description: "Hiện đại, bố cục hai cột nổi bật." },
  { value: "compact", label: "Compact", description: "Mật độ thông tin cao, tự động phân trang khi dài." },
];

export const CV_DESIGNS = DEFAULT_CV_TEMPLATES;

export const CV_DESIGN_LABELS: Record<string, string> = {
  classic_ats: "Classic ATS",
  modern_professional: "Modern Professional",
  compact: "Compact",
  compact_one_page: "Compact",
};

export function templateDefinitionsToDesigns(templates: CVTemplateDefinition[]): CVDesignDefinition[] {
  return templates.map((t) => ({
    value: t.template_id as CVDesign,
    label: t.label,
    description: t.description,
  }));
}
