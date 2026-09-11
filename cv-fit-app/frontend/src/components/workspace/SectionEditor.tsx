"use client";

import { Trash2 } from "lucide-react";
import type { CVBlock, CVSection } from "@/types";
import { EntryForm } from "./EntrySectionEditor";
import { EducationForm } from "./EducationSectionEditor";
import { SkillGroupForm } from "./SkillGroupSectionEditor";
import { PublicationForm } from "./PublicationSectionEditor";
import { ParagraphForm } from "./ParagraphSectionEditor";
import { UnknownForm } from "./UnknownSectionEditor";
import { freshBlockId } from "@/lib/cv-edit-utils";
import PrivacyToggle from "./PrivacyToggle";

type BlockPatch = Partial<CVBlock>;

function BlockEditor({
  block,
  onChange,
  onToggleHidden,
}: {
  block: CVBlock;
  onChange: (patch: BlockPatch) => void;
  onToggleHidden?: () => void;
}) {
  switch (block.type) {
    case "entry":
      return <EntryForm block={block} onChange={onChange} onToggleHidden={onToggleHidden} />;
    case "education":
      return <EducationForm block={block} onChange={onChange} onToggleHidden={onToggleHidden} />;
    case "skill_group":
      return <SkillGroupForm block={block} onChange={onChange} onToggleHidden={onToggleHidden} />;
    case "publication":
      return <PublicationForm block={block} onChange={onChange} onToggleHidden={onToggleHidden} />;
    case "paragraph":
      return <ParagraphForm block={block} onChange={onChange} onToggleHidden={onToggleHidden} />;
    case "bullet":
      return (
        <div className="space-y-1">
          <input
            type="text"
            value={block.text ?? ""}
            placeholder="Nội dung"
            onChange={(e) => onChange({ text: e.target.value })}
            className="w-full rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-sm text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:outline-none focus:ring-2 focus:ring-[#2D7A58]/10 transition-all"
          />
        </div>
      );
    case "unknown":
      return <UnknownForm block={block} onChange={onChange} onToggleHidden={onToggleHidden} />;
    default: {
      // Generic fallback: never render nothing — every current and future
      // block type (languages / awards / activities / custom) stays editable.
      const maybeText = (block as { text?: unknown }).text;
      if (typeof maybeText === "string") {
        return (
          <ParagraphForm
            block={{ ...(block as object), type: "paragraph", text: maybeText } as Parameters<typeof ParagraphForm>[0]["block"]}
            onChange={onChange as Parameters<typeof ParagraphForm>[0]["onChange"]}
            onToggleHidden={onToggleHidden}
          />
        );
      }
      const maybeLines = (block as { lines?: unknown }).lines;
      if (Array.isArray(maybeLines)) {
        return (
          <UnknownForm
            block={{ ...(block as object), type: "unknown", lines: maybeLines as string[], confidence: (block as { confidence?: number }).confidence ?? 0.5 } as Parameters<typeof UnknownForm>[0]["block"]}
            onChange={onChange as Parameters<typeof UnknownForm>[0]["onChange"]}
            onToggleHidden={onToggleHidden}
          />
        );
      }
      return <UnknownForm block={{ type: "unknown", block_id: (block as { block_id?: string }).block_id ?? "unknown", lines: [], confidence: 0.5, ...(block as object) } as Parameters<typeof UnknownForm>[0]["block"]} onChange={onChange as Parameters<typeof UnknownForm>[0]["onChange"]} onToggleHidden={onToggleHidden} />;
    }
  }
}

interface Props {
  section: CVSection;
  onBlockChange: (blockId: string, patch: BlockPatch) => void;
  onToggleHidden: (blockId: string) => void;
  onAddBlock?: (block: CVBlock) => void;
  onRemoveBlock?: (blockId: string) => void;
}

export default function SectionEditor({ section, onBlockChange, onToggleHidden, onAddBlock, onRemoveBlock }: Props) {
  const normalizedTitle = section.title ?? "";
  const isSkillSection = section.type === "skills" || /skill/i.test(normalizedTitle);
  const isCertSection = section.type === "certifications" || /certif/i.test(normalizedTitle);
  // Generic list sections (languages / awards / activities / interests / custom)
  // store one line per bullet/paragraph — editable without a bespoke form.
  const isListSection =
    section.type === "languages" ||
    section.type === "awards" ||
    section.type === "activities" ||
    section.type === "interests" ||
    section.type === "custom" ||
    /ngôn ngữ|language|giải thưởng|award|honor|hoạt động|activit|sở thích|interest|additional|other|bổ sung/i.test(normalizedTitle);
  const targetType = isSkillSection ? "skill_group" : (
    section.blocks[0]?.type ?? (
      section.type === "experience" || section.type === "projects" || isCertSection ? "entry"
      : section.type === "education" ? "education"
      : section.type === "publications" ? "publication"
      : isListSection ? "bullet"
      : undefined
    )
  );
  const supportsAdd = !!onAddBlock && (targetType === "entry" || targetType === "education" || targetType === "skill_group" || targetType === "publication" || targetType === "bullet" || targetType === "paragraph" || targetType === "unknown");

  return (
    <div className="space-y-6">
      {section.blocks.length === 0 ? (
        <p className="text-xs text-gray-400 italic py-2">Chưa có mục nào trong phần này.</p>
      ) : (
        <div className="space-y-6 divide-y divide-gray-100">
          {section.blocks.map((block, idx) => (
            <div key={block.block_id} className={`space-y-2 ${idx > 0 ? "pt-6" : ""}`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 tracking-wide uppercase">
                  Mục #{idx + 1}
                </span>
                <div className="flex items-center gap-1.5">
                  <PrivacyToggle
                    hidden={!!block.hidden}
                    onToggle={() => onToggleHidden(block.block_id)}
                    label="mục này"
                  />
                  {onRemoveBlock && (
                    <button
                      type="button"
                      onClick={() => onRemoveBlock(block.block_id)}
                      className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-700 transition-colors"
                      aria-label="Xóa mục này"
                      title="Xóa mục này"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
              <BlockEditor
                block={block}
                onChange={(patch) => onBlockChange(block.block_id, patch)}
                onToggleHidden={() => onToggleHidden(block.block_id)}
              />
            </div>
          ))}
        </div>
      )}
      {supportsAdd && (
        <button
          type="button"
          onClick={() => {
            const id = freshBlockId(targetType!);
            const base = { block_id: id, origin: "user_edit" as const };
            let block: CVBlock;
            switch (targetType) {
              case "entry":
                block = { ...base, type: "entry", title: "", bullets: [] };
                break;
              case "education":
                block = { ...base, type: "education", details: [] };
                break;
              case "skill_group":
                block = { ...base, type: "skill_group", skills: [] };
                break;
              case "publication":
                block = { ...base, type: "publication", title: "" };
                break;
              case "bullet":
                block = { ...base, type: "bullet", text: "" } as CVBlock;
                break;
              case "paragraph":
                block = { ...base, type: "paragraph", text: "" } as CVBlock;
                break;
              case "unknown":
                block = { ...base, type: "unknown", lines: [""], confidence: 1 } as unknown as CVBlock;
                break;
              default:
                return;
            }
            onAddBlock(block);
          }}
          className="inline-flex items-center gap-1.5 rounded-xl border border-dashed border-[#2D7A58]/40 px-3.5 py-2 text-xs font-semibold text-[#2D7A58] hover:bg-[#EAF5EC]/50 transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Thêm mục
        </button>
      )}
    </div>
  );
}
