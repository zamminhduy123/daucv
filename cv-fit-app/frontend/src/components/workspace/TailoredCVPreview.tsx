"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Link as Linkedin, Mail, MapPin, Phone } from "lucide-react";
import { CV_DESIGN_LABELS, cvSectionKind } from "@/lib/cv-designs";
import type { CVDesign, TailoredCV, TailoredCVSection } from "@/types";
import type { CVBlockType, CVDocumentV2 } from "@/types";
import { v1ToV2 } from "@/lib/cv-v1-to-v2-adapter";

// ---------------------------------------------------------------------------
// V1 types (legacy)
// ---------------------------------------------------------------------------

function normalizeSectionItems(items: string[]) {
  return items.reduce<string[]>((normalized, item) => {
    const stripped = item.trim();
    const previous = normalized.at(-1);
    if (previous?.match(/^[•●▪◦]/) && stripped && /^\p{Ll}/u.test(stripped)) {
      normalized[normalized.length - 1] = `${previous.trimEnd()} ${stripped}`;
    } else {
      normalized.push(item);
    }
    return normalized;
  }, []);
}

function normalizeSections(sections: TailoredCVSection[]) {
  return sections.map((section) => ({ ...section, items: normalizeSectionItems(section.items) }));
}

// Kept as the legacy-template input path for rollback compatibility.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function getSections(cv: TailoredCV): TailoredCVSection[] {
  if (cv.sections?.length) return normalizeSections(cv.sections);
  return normalizeSections([
    ...(cv.experience?.length
      ? [{ title: "Experience", items: cv.experience.flatMap((item) => [`${item.role} — ${item.company}`, ...item.bullet_points]) }]
      : []),
    ...(cv.skills?.length ? [{ title: "Skills", items: cv.skills }] : []),
    ...(cv.education ? [{ title: "Education", items: [cv.education] }] : []),
  ]);
}

function cleanBullet(item: string) {
  return item.replace(/^[•●▪◦]\s*/, "");
}

function isEntryHeadline(items: string[], index: number) {
  if (items[index].match(/^[•●▪◦]\s*/)) return false;
  return index === 0 || items[index - 1].match(/^[•●▪◦]\s*/);
}

function documentLabels(language: "vi" | "en") {
  return language === "vi"
    ? { profile: "Tóm tắt", contact: "Liên hệ" }
    : { profile: "Profile", contact: "Contact" };
}

function ContactIcon({ line }: { line: string }) {
  const value = line.toLowerCase();
  if (value.includes("@")) return <Mail size={12} />;
  if (value.includes("linkedin")) return <Linkedin size={12} />;
  if (/\d{3}/.test(value)) return <Phone size={12} />;
  return <MapPin size={12} />;
}

type TemplateProps = {
  cv: TailoredCV;
  sections: TailoredCVSection[];
  language: "vi" | "en";
};

function ClassicTemplate({ cv, sections, language }: TemplateProps) {
  const labels = documentLabels(language);
  return <article className="cv-print mx-auto min-h-[1123px] w-full max-w-[794px] bg-white p-10 text-gray-900 shadow-xl md:p-12" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
    <header className="border-b border-gray-400 pb-5 text-left">
      <h1 className="mb-1 text-3xl font-black uppercase tracking-[0.08em] text-gray-950">{cv.name || "CV"}</h1>
      {cv.headline && <p className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-gray-700">{cv.headline}</p>}
      {!!cv.contact_lines?.length && <p className="text-[11px] leading-relaxed text-gray-600">{cv.contact_lines.join(" | ")}</p>}
    </header>

    {cv.summary && <section className="mt-7 text-[12px] leading-relaxed">
      <div className="mb-3 border-b border-gray-400 pb-1"><h2 className="text-sm font-black uppercase tracking-[0.16em] text-gray-950">{labels.profile}</h2></div>
      <p className="text-gray-800">{cv.summary}</p>
    </section>}

    <div className="mt-7 space-y-7 text-[12px] leading-relaxed">
      {sections.map((section) => <section key={section.title}>
        <div className="mb-3 border-b border-gray-400 pb-1"><h2 className="text-sm font-black uppercase tracking-[0.16em] text-gray-950">{section.title}</h2></div>
        <div className="space-y-1 text-gray-800">
          {section.items.map((item, index) => item.match(/^[•●▪◦]\s*/)
            ? <p key={index} className="ml-4 pl-1 before:-ml-3 before:mr-2 before:content-['•']">{cleanBullet(item)}</p>
            : <p key={index} className={`whitespace-pre-line ${isEntryHeadline(section.items, index) ? "font-bold" : "font-normal"}`}>{item}</p>)}
        </div>
      </section>)}
    </div>
  </article>;
}

function CompactTemplate({ cv, sections, language }: TemplateProps) {
  const labels = documentLabels(language);
  const documentRef = useRef<HTMLElement>(null);
  const [scale, setScale] = useState(1);
  useLayoutEffect(() => {
    const document = documentRef.current;
    if (!document) return;
    const fit = () => setScale(Math.min(1, 1123 / document.scrollHeight));
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(document);
    return () => observer.disconnect();
  }, [cv, sections]);
  return <div className="mx-auto h-[1123px] w-full max-w-[794px] overflow-hidden bg-white shadow-xl">
    <article ref={documentRef} className="cv-print min-h-[1123px] w-full origin-top-left bg-white font-sans text-gray-800" style={{ transform: `scale(${scale})` }}>
    <div className="h-1 w-full bg-[#4A90A4]" />
    <div className="p-7 md:p-9">
      <header className="mb-5">
        <h1 className="mb-1 text-2xl font-black tracking-tight text-gray-950">{cv.name || "CV"}</h1>
        <p className="text-[11px] font-medium leading-snug text-gray-600">{[cv.headline, ...(cv.contact_lines || [])].filter(Boolean).join(" · ")}</p>
      </header>

      <div className="space-y-4 text-xs leading-snug">
        {cv.summary && <section>
          <h2 className="mb-2 border-l-2 border-[#4A90A4] pl-2 text-sm font-semibold uppercase tracking-[0.12em] text-gray-900">{labels.profile}</h2>
          <p className="text-gray-700">{cv.summary}</p>
        </section>}
        {sections.map((section) => <section key={section.title}>
          <h2 className="mb-2 border-l-2 border-[#4A90A4] pl-2 text-sm font-semibold uppercase tracking-[0.12em] text-gray-900">{section.title}</h2>
          {cvSectionKind(section.title) === "skills"
            ? <div className="flex flex-wrap gap-1.5">{section.items.map((item, index) => <span key={index} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">{cleanBullet(item)}</span>)}</div>
            : <div className="space-y-1 text-gray-700">{section.items.map((item, index) => item.match(/^[•●▪◦]\s*/)
              ? <p key={index} className="ml-4 list-item list-disc">{cleanBullet(item)}</p>
              : <p key={index} className={`whitespace-pre-line ${isEntryHeadline(section.items, index) ? "font-bold text-gray-950" : "font-medium"}`}>{item}</p>)}</div>}
        </section>)}
      </div>
    </div>
    </article>
  </div>;
}

function ModernTemplate({ cv, sections, language }: TemplateProps) {
  const labels = documentLabels(language);
  const skillSections = sections.filter((section) => cvSectionKind(section.title) === "skills");
  const educationSections = sections.filter((section) => cvSectionKind(section.title) === "education");
  const sidebarSections = new Set([...skillSections, ...educationSections]);
  const mainSections = sections.filter((section) => !sidebarSections.has(section));

  return <article className="cv-print mx-auto flex min-h-[1123px] w-full max-w-[794px] overflow-hidden bg-white font-sans text-[#2F4F4F] shadow-xl">
    <aside className="w-[32%] shrink-0 bg-[#6A9B5E] px-6 py-8 text-white">
      <div className="mb-8">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-white/80 bg-white/10 text-lg font-black tracking-wider">{initials(cv.name)}</div>
        <h1 className="text-2xl font-black leading-tight tracking-tight text-white">{cv.name || "CV"}</h1>
        {cv.headline && <p className="mt-1 text-sm font-medium text-white/70">{cv.headline}</p>}
      </div>

      {!!cv.contact_lines?.length && <section className="mb-7">
        <h2 className="mb-3 text-[11px] font-black uppercase tracking-[0.18em] text-white">{labels.contact}</h2>
        <div className="space-y-2.5 text-[11px] leading-snug text-white">
          {cv.contact_lines.map((line, index) => <div key={index} className="flex items-start gap-2 break-words"><span className="mt-0.5 shrink-0 text-white/80"><ContactIcon line={line} /></span><span className="min-w-0">{line}</span></div>)}
        </div>
      </section>}

      {skillSections.map((section) => <section key={section.title} className="mb-7">
        <h2 className="mb-3 text-[11px] font-black uppercase tracking-[0.18em] text-white">{section.title}</h2>
        <div className="flex flex-wrap gap-1.5">{section.items.map((item, index) => <span key={index} className="rounded-full bg-white/20 px-2 py-1 text-[10px] font-bold text-white">{cleanBullet(item)}</span>)}</div>
      </section>)}

      {educationSections.map((section) => <section key={section.title} className="mb-7 last:mb-0">
        <h2 className="mb-3 text-[11px] font-black uppercase tracking-[0.18em] text-white">{section.title}</h2>
        <div className="space-y-2 text-[11px] leading-snug text-white">{section.items.map((item, index) => <p key={index} className={index === 0 ? "font-bold" : "text-white/75"}>{cleanBullet(item)}</p>)}</div>
      </section>)}
    </aside>

    <div className="w-[68%] px-8 py-9">
      <div className="space-y-7">
        {cv.summary && <section>
          <div className="mb-3 border-l-4 border-[#6A9B5E] pl-3"><h2 className="text-sm font-black uppercase tracking-[0.16em] text-[#6A9B5E]">{labels.profile}</h2></div>
          <p className="text-[11px] leading-relaxed text-gray-600">{cv.summary}</p>
        </section>}
        {mainSections.map((section) => <section key={section.title}>
          <div className="mb-3 border-l-4 border-[#6A9B5E] pl-3"><h2 className="text-sm font-black uppercase tracking-[0.16em] text-[#6A9B5E]">{section.title}</h2></div>
          <div className="space-y-1.5 text-[11px] leading-relaxed text-gray-600">{section.items.map((item, index) => item.match(/^[•●▪◦]\s*/)
            ? <div key={index} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#6A9B5E]" /><span>{cleanBullet(item)}</span></div>
            : <p key={index} className={`whitespace-pre-line text-[#2F4F4F] ${isEntryHeadline(section.items, index) ? "text-sm font-black" : "font-medium"}`}>{item}</p>)}</div>
        </section>)}
      </div>
    </div>
  </article>;
}

// Kept with the legacy templates for rollback compatibility.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const DESIGN_RENDERERS: Record<CVDesign, typeof ClassicTemplate> = {
  classic_ats: ClassicTemplate,
  modern_professional: ModernTemplate,
  compact_one_page: CompactTemplate,
};

function initials(name?: string) {
  return (name || "CV")
    .trim()
    .split(/\s+/)
    .slice(-3)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

// ---------------------------------------------------------------------------
// V2 iframe renderer — uses srcdoc so the V2 HTML renders identically in
// preview and download.  Both preview and PDF generation share this HTML.
// ---------------------------------------------------------------------------

function V2IframeRenderer({ doc, design, language }: { doc: CVDocumentV2; design: CVDesign; language: "vi" | "en" }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useLayoutEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    iframe.srcdoc = buildV2Html(doc, design, language);
  }, [doc, design, language]);

  return <iframe ref={iframeRef} className="h-[1123px] w-full max-w-[794px] border-0 bg-white shadow-xl" title="CV Preview (V2)" />;
}

function buildV2Html(doc: CVDocumentV2, design: CVDesign, language: "vi" | "en") {
  const contacts = (doc.identity.contact_lines || []).map(esc).join(" · ");
  const profileLabel = language === "vi" ? "Tóm tắt" : "Profile";
  const contactLabel = language === "vi" ? "Liên hệ" : "Contact";

  let summaryHtml = "";
  if (doc.summary) summaryHtml = `<section><h2>${esc(profileLabel)}</h2><p class="item">${esc(doc.summary.text)}</p></section>`;

  const sectionsHtml = doc.sections
    .filter((s) => s.type !== "summary")
    .map((s) => {
      const blocks = s.blocks.map(renderBlock).join("");
      return `<section><h2>${esc(s.title)}</h2>${blocks}</section>`;
    })
    .join("");

  let header = `<header><h1>${esc(doc.identity.name || "CV")}</h1><h3>${esc(doc.identity.headline || "")}</h3><p class="contacts">${contacts}</p></header>`;
  let body = `${summaryHtml}${sectionsHtml}`;

  if (design === "modern_professional") {
    const sidebar = doc.sections.filter((s) => s.type === "skills" || s.type === "education");
    const main = doc.sections.filter((s) => s.type !== "skills" && s.type !== "education" && s.type !== "summary");
    body = `<aside>${header}<section><h2>${esc(contactLabel)}</h2><p class="item">${contacts}</p></section>${sidebar.map((s) => `<section><h2>${esc(s.title)}</h2>${s.blocks.map(renderBlock).join("")}</section>`).join("")}</aside><main>${summaryHtml}${main.map((s) => `<section><h2>${esc(s.title)}</h2>${s.blocks.map(renderBlock).join("")}</section>`).join("")}</main>`;
    header = "";
  }

  const css = `
    @page { size: A4; margin: 0; } * { box-sizing: border-box; }
    body { margin: 0; color: #263b3b; font-family: Arial, sans-serif; }
    article { width: 210mm; min-height: 297mm; background: white; padding: 16mm; }
    header { border-bottom: 1px solid #9ca3af; padding-bottom: 5mm; }
    h1 { margin: 0 0 1mm; font-size: 24pt; } h3 { margin: 0 0 3mm; font-size: 11pt; }
    .contacts { color: #596565; font-size: 8.5pt; } section { margin-top: 6mm; break-inside: avoid; }
    h2 { margin: 0 0 2.5mm; border-bottom: 1px solid #9ca3af; padding-bottom: 1mm; font-size: 10pt; text-transform: uppercase; letter-spacing: 1.2px; }
    .item, .bullet { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; white-space: pre-wrap; }
    .entry-title { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; font-weight: 700; white-space: pre-wrap; }
    .entry-subtitle, .entry-meta { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; font-weight: 400; color: #555; white-space: pre-wrap; }
    .bullet { padding-left: 4mm; } .bullet::before { content: '\\2022'; margin-left: -3mm; margin-right: 2mm; }
    .skills { font-size: 8.5pt; color: #333; }
    .publication { font-size: 9pt; font-style: italic; }
    .classic_ats { font-family: Georgia, 'Times New Roman', serif; }
    .compact_one_page { border-top: 1.5mm solid #4A90A4; padding: 10mm 13mm; }
    .compact_one_page section { margin-top: 3.5mm; } .compact_one_page h2 { border: 0; border-left: 1mm solid #4A90A4; padding-left: 2mm; }
    .compact_one_page .item, .compact_one_page .bullet { font-size: 8pt; line-height: 1.3; margin-bottom: 1mm; }
    .modern_professional { display: flex; padding: 0; } .modern_professional > aside { width: 32%; min-height: 297mm; padding: 14mm 8mm; background: #6A9B5E; color: white; }
    .modern_professional > main { width: 68%; padding: 14mm 10mm; } .modern_professional aside header { border-color: rgba(255,255,255,.5); }
    .modern_professional aside h1 { font-size: 19pt; } .modern_professional aside h2 { border-color: rgba(255,255,255,.5); }
    .modern_professional main h2 { color: #6A9B5E; border: 0; border-left: 1mm solid #6A9B5E; padding-left: 2mm; }
  `;
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body><article class="${design}">${header}${body}</article></body></html>`;
}

function renderBlock(block: CVBlockType): string {
  if (block.type === "entry") {
    let h = `<p class="entry-title">${esc(block.title)}</p>`;
    if (block.subtitle) h += `<p class="entry-subtitle">${esc(block.subtitle)}</p>`;
    const metadata = [block.organization, block.location, block.date].filter(isPresent).map(esc).join(" · ");
    if (metadata) h += `<p class="entry-meta">${metadata}</p>`;
    for (const b of block.bullets || []) h += `<p class="bullet">${esc(b)}</p>`;
    return h;
  }
  if (block.type === "bullet") return `<p class="bullet">${esc(block.text)}</p>`;
  if (block.type === "paragraph") return `<p class="item">${esc(block.text)}</p>`;
  if (block.type === "skill_group") {
    let h = block.label ? `<p class="entry-title">${esc(block.label)}</p>` : "";
    h += `<p class="skills">${(block.skills || []).map(esc).join(" · ")}</p>`;
    return h;
  }
  if (block.type === "publication") {
    let h = `<p class="publication">${esc(block.title)}</p>`;
    if (block.authors) h += `<p class="item">${esc(block.authors)}</p>`;
    const metadata = [block.venue, block.date, block.status].filter(isPresent).map(esc).join(" · ");
    if (metadata) h += `<p class="item">${metadata}</p>`;
    return h;
  }
  if (block.type === "education") {
    let h = block.institution ? `<p class="entry-title">${esc(block.institution)}</p>` : "";
    const educationTitle = [block.degree, block.field].filter(isPresent).map(esc).join(" — ");
    if (educationTitle) h += `<p class="entry-subtitle">${educationTitle}</p>`;
    const metadata = [block.location, block.date].filter(isPresent).map(esc).join(" · ");
    if (metadata) h += `<p class="entry-meta">${metadata}</p>`;
    for (const d of block.details || []) h += `<p class="item">${esc(d)}</p>`;
    return h;
  }
  if (block.type === "unknown") return `<p class="item">${esc((block.lines || []).join(" | "))}</p>`;
  return "";
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function isPresent(value: string | undefined): value is string {
  return Boolean(value);
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function TailoredCVPreview({
  cv,
  design,
  document_v2,
  language = "vi",
  onDownload,
}: {
  cv: TailoredCV;
  design: CVDesign;
  document_v2?: CVDocumentV2 | null;
  language?: "vi" | "en";
  onDownload?: () => void;
}) {
  // V2 path: render using typed blocks
  if (document_v2) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between print:hidden">
          <p className="text-sm font-bold text-[#2F4F4F]">{CV_DESIGN_LABELS[design]}</p>
          {onDownload && <button type="button" onClick={onDownload} className="rounded-xl bg-[#6A9B5E] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:bg-[#5a874e] active:scale-95">Tải PDF</button>}
        </div>
        <V2IframeRenderer doc={document_v2} design={design} language={language} />
      </div>
    );
  }

  // V1 path: adapt to V2 for consistent rendering
  const adaptedV2 = v1ToV2(
    cv.name,
    cv.headline,
    cv.contact_lines,
    cv.summary,
    cv.sections,
    cv.experience,
    cv.skills,
    cv.education,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <p className="text-sm font-bold text-[#2F4F4F]">{CV_DESIGN_LABELS[design]}</p>
        {onDownload && <button type="button" onClick={onDownload} className="rounded-xl bg-[#6A9B5E] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:bg-[#5a874e] active:scale-95">Tải PDF</button>}
      </div>
      <V2IframeRenderer doc={adaptedV2} design={design} language={language} />
    </div>
  );
}
