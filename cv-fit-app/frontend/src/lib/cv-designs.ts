import type { CVDesign } from "@/types";

export interface CVDesignDefinition {
  value: CVDesign;
  label: string;
  description: string;
}

export const CV_DESIGNS: readonly CVDesignDefinition[] = [
  { value: "classic_ats", label: "Classic ATS", description: "Tối ưu ATS, đơn giản, chuyên nghiệp." },
  { value: "modern_professional", label: "Modern Professional", description: "Hiện đại, bố cục hai cột, nổi bật." },
  { value: "compact_one_page", label: "Compact One-Page", description: "Gọn gàng, vừa một trang, đầy đủ nội dung." },
];

export const CV_DESIGN_LABELS = Object.fromEntries(
  CV_DESIGNS.map((design) => [design.value, design.label]),
) as Record<CVDesign, string>;
