import type { CVBlockType, CVDesign, CVDocumentV2, CVSection } from "@/types";
import { identityContactLines } from "./cv-identity-compat.js";

export function buildCVHtml(doc: CVDocumentV2, design: CVDesign, language: "vi" | "en") {
  const contacts = identityContactLines(doc.identity).map(escapeHtml).join(" · ");
  const profile = language === "vi" ? "Tóm tắt" : "Profile";
  const summary = doc.summary ? `<section><h2>${profile}</h2>${renderBlock(doc.summary)}</section>` : "";
  const sections = doc.sections.filter((section) => section.type !== "summary");
  let header = `<header><h1>${escapeHtml(doc.identity.full_name || doc.identity.name || "CV")}</h1><h3>${escapeHtml(doc.identity.headline || "")}</h3><p class="contacts">${contacts}</p></header>`;
  let body = `${summary}${sections.map(renderSection).join("")}`;

  if (design === "modern_professional") {
    const sidebar = sections.filter((section) => section.type === "skills" || section.type === "education");
    const main = sections.filter((section) => section.type !== "skills" && section.type !== "education");
    body = `<aside>${header}${sidebar.map(renderSection).join("")}</aside><main>${summary}${main.map(renderSection).join("")}</main>`;
    header = "";
  }

  const warning = design === "compact" && compactRenderingWarnings(doc).length
    ? ' data-render-warning="compact_template_content_exceeds_one_page"'
    : "";
  return `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style></head><body${warning}><article class="${design}">${header}${body}</article></body></html>`;
}

export function compactRenderingWarnings(doc: CVDocumentV2): string[] {
  return estimatedRenderLines(doc) > 62
    ? ["compact_template_content_exceeds_one_page"]
    : [];
}

function estimatedRenderLines(doc: CVDocumentV2) {
  let lines = 2 + identityContactLines(doc.identity).length;
  if (doc.summary) lines += 2 + wrappedLines(doc.summary.text);
  for (const section of doc.sections) {
    lines += 2;
    for (const block of section.blocks) {
      if (block.type === "entry") {
        lines += 1 + Number(Boolean(block.subtitle || block.organization));
        lines += Number(Boolean(block.location || block.date));
        lines += block.bullets.reduce((total, item) => total + wrappedLines(item), 0);
      } else if (block.type === "skill_group") {
        lines += wrappedLines(block.skills.join(", "), 72);
      } else if (block.type === "publication") {
        lines += wrappedLines([block.authors, block.title, block.venue, block.date, block.status].filter(isPresent).join(" "));
      } else if (block.type === "education") {
        lines += 2 + block.details.reduce((total, item) => total + wrappedLines(item), 0);
      } else if (block.type === "unknown") {
        lines += block.lines.reduce((total, item) => total + wrappedLines(item), 0);
      } else {
        lines += wrappedLines(block.text);
      }
    }
  }
  return lines;
}

function wrappedLines(text: string, width = 88) {
  return Math.max(1, Math.ceil(text.trim().length / width));
}

function renderSection(section: CVSection) {
  if (section.type === "custom" && section.title?.toLowerCase().includes("unclassified")) {
    return "";
  }
  return `<section data-section-type="${section.type}"><h2>${escapeHtml(section.title)}</h2>${section.blocks.map(renderBlock).join("")}</section>`;
}

function renderBlock(block: CVBlockType): string {
  const confidence = block.confidence ?? (block.type === "unknown" ? 0 : 1);
  const attributes = `data-block-type="${block.type}" data-confidence="${confidence.toFixed(2)}"`;
  if (confidence < 0.8 && !["bullet", "paragraph", "unknown"].includes(block.type)) {
    return `<div class="neutral-block" ${attributes}><p class="item">${escapeHtml(blockText(block))}</p></div>`;
  }
  if (block.type === "entry") {
    const metadata = [block.organization, block.location, block.date].filter(isPresent).map(escapeHtml).join(" · ");
    return `<div ${attributes}><p class="entry-title">${escapeHtml(block.title)}</p>${block.subtitle ? `<p class="entry-subtitle">${escapeHtml(block.subtitle)}</p>` : ""}${metadata ? `<p class="entry-meta">${metadata}</p>` : ""}${block.bullets.map((bullet) => `<p class="bullet">${escapeHtml(bullet)}</p>`).join("")}</div>`;
  }
  if (block.type === "bullet") return `<p class="bullet" ${attributes}>${escapeHtml(block.text)}</p>`;
  if (block.type === "paragraph") return `<p class="item" ${attributes}>${escapeHtml(block.text)}</p>`;
  if (block.type === "skill_group") return `<div ${attributes}>${block.label ? `<p class="entry-title">${escapeHtml(block.label)}</p>` : ""}<p class="skills">${block.skills.map(escapeHtml).join(" · ")}</p></div>`;
  if (block.type === "publication") {
    const metadata = [block.venue, block.date, block.status].filter(isPresent).map(escapeHtml).join(" · ");
    return `<div ${attributes}><p class="publication">${escapeHtml(block.title)}</p>${block.authors ? `<p class="item">${escapeHtml(block.authors)}</p>` : ""}${metadata ? `<p class="item">${metadata}</p>` : ""}</div>`;
  }
  if (block.type === "education") {
    const degree = [block.degree, block.field].filter(isPresent).map(escapeHtml).join(" — ");
    const metadata = [block.location, block.date].filter(isPresent).map(escapeHtml).join(" · ");
    return `<div ${attributes}>${block.institution ? `<p class="entry-title">${escapeHtml(block.institution)}</p>` : ""}${degree ? `<p class="entry-subtitle">${degree}</p>` : ""}${metadata ? `<p class="entry-meta">${metadata}</p>` : ""}${block.details.map((detail) => `<p class="item">${escapeHtml(detail)}</p>`).join("")}</div>`;
  }
  return `<p class="item unknown" ${attributes}>${escapeHtml(block.lines.join(" | "))}</p>`;
}

function blockText(block: CVBlockType) {
  if (block.type === "entry") return [block.title, block.subtitle, block.organization, block.location, block.date, ...block.bullets].filter(isPresent).join(" | ");
  if (block.type === "skill_group") return [block.label, ...block.skills].filter(isPresent).join(" | ");
  if (block.type === "publication") return [block.title, block.authors, block.venue, block.date, block.status].filter(isPresent).join(" | ");
  if (block.type === "education") return [block.institution, block.degree, block.field, block.location, block.date, ...block.details].filter(isPresent).join(" | ");
  if (block.type === "unknown") return block.lines.join(" | ");
  return block.text;
}

function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function isPresent(value: string | null | undefined): value is string { return Boolean(value); }

const CSS = `
@page { size: A4; margin: 0; } * { box-sizing: border-box; }
html, body { margin: 0; color: #263b3b; font-family: Arial, sans-serif; }
article { width: 210mm; min-height: 297mm; background: white; padding: 16mm; }
header { border-bottom: 1px solid #9ca3af; padding-bottom: 5mm; }
h1 { margin: 0 0 1mm; font-size: 24pt; } h3 { margin: 0 0 3mm; font-size: 11pt; }
.contacts { color: #596565; font-size: 8.5pt; } section { margin-top: 6mm; break-inside: avoid; }
h2 { margin: 0 0 2.5mm; border-bottom: 1px solid #9ca3af; padding-bottom: 1mm; font-size: 10pt; text-transform: uppercase; letter-spacing: 1.2px; }
.item, .bullet, .entry-title, .entry-subtitle, .entry-meta { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; white-space: pre-wrap; }
.entry-title { font-weight: 700; } .entry-subtitle, .entry-meta { color: #555; }
.bullet { padding-left: 4mm; } .bullet::before { content: '\\2022'; margin-left: -3mm; margin-right: 2mm; }
.skills { font-size: 8.5pt; color: #333; } .publication { font-size: 9pt; font-style: italic; }
.unknown, .neutral-block { font-weight: 400; font-style: normal; }
.classic_ats { font-family: Georgia, 'Times New Roman', serif; }
.compact_one_page { border-top: 1.5mm solid #4A90A4; padding: 10mm 13mm; }
.compact_one_page section { margin-top: 3.5mm; } .compact_one_page h2 { border: 0; border-left: 1mm solid #4A90A4; padding-left: 2mm; }
.compact_one_page .item, .compact_one_page .bullet, .compact_one_page .entry-title, .compact_one_page .entry-subtitle, .compact_one_page .entry-meta { font-size: 8pt; line-height: 1.3; margin-bottom: 1mm; }
.modern_professional { display: flex; padding: 0; } .modern_professional > aside { width: 32%; min-height: 297mm; padding: 14mm 8mm; background: #6A9B5E; color: white; }
.modern_professional > main { width: 68%; padding: 14mm 10mm; } .modern_professional aside h1 { font-size: 19pt; }
.modern_professional aside h2 { border-color: rgba(255,255,255,.5); } .modern_professional main h2 { color: #6A9B5E; border: 0; border-left: 1mm solid #6A9B5E; padding-left: 2mm; }
`;
