"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Link as Linkedin, Mail, MapPin, Phone } from "lucide-react";
import { CV_DESIGN_LABELS, cvSectionKind } from "@/lib/cv-designs";
import type { CVDesign, TailoredCV, TailoredCVSection } from "@/types";

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

function initials(name?: string) {
  return (name || "CV")
    .trim()
    .split(/\s+/)
    .slice(-3)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
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

const DESIGN_RENDERERS: Record<CVDesign, typeof ClassicTemplate> = {
  classic_ats: ClassicTemplate,
  modern_professional: ModernTemplate,
  compact_one_page: CompactTemplate,
};

export default function TailoredCVPreview({ cv, design, language = "vi", onDownload }: { cv: TailoredCV; design: CVDesign; language?: "vi" | "en"; onDownload?: () => void }) {
  const sections = getSections(cv);
  const Renderer = DESIGN_RENDERERS[design];
  return <div className="space-y-4">
    <div className="flex items-center justify-between print:hidden">
      <p className="text-sm font-bold text-[#2F4F4F]">{CV_DESIGN_LABELS[design]}</p>
      {onDownload && <button type="button" onClick={onDownload} className="rounded-xl bg-[#6A9B5E] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#6A9B5E]/20 transition hover:bg-[#5a874e] active:scale-95">Tải PDF</button>}
    </div>
    <Renderer cv={cv} sections={sections} language={language} />
    <style>{`@media print { body * { visibility: hidden; } .cv-print, .cv-print * { visibility: visible; } .cv-print { position: absolute; left: 0; top: 0; width: 210mm; min-height: 297mm; max-width: none; border: 0; box-shadow: none; } .compact_one_page { max-height: 297mm !important; overflow: hidden !important; } @page { size: A4; margin: 0; } }`}</style>
  </div>;
}
