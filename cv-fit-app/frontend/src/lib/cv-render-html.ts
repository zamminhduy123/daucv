import type { CVBlockType, CVDesign, CVDocumentV2, CVSection } from "@/types";
import { identityContactLines } from "./cv-identity-compat.js";

export interface CVTypographyConfig {
  fontFamily?: string;
  fontSize?: string; // Backward compatibility
  baseFontSize?: number; // Base font size in pt (e.g. 9.5)
  lineHeight?: number | string; // Line height multiplier (e.g. 1.4)
  sectionSpacing?: number; // Space between sections in mm (e.g. 4.0)
  itemSpacing?: number; // Space between entries/items in mm (e.g. 3.0)
  pageMargin?: number; // Page padding/margins in mm (e.g. 12)
}

export function buildCVHtml(
  doc: CVDocumentV2,
  design: CVDesign,
  language: "vi" | "en",
  typography?: CVTypographyConfig,
) {
  // v1 privacy: zero out identity fields the user has hidden before rendering.
  // A shallow copy is enough — identityContactLines only reads scalar fields.
  const hiddenFields = new Set(doc.identity.hidden_fields ?? []);
  const visibleIdentity: CVDocumentV2["identity"] = hiddenFields.size
    ? {
        ...doc.identity,
        full_name: hiddenFields.has("full_name") ? null : doc.identity.full_name,
        headline: hiddenFields.has("headline") ? null : doc.identity.headline,
        email: hiddenFields.has("email") ? null : doc.identity.email,
        phone: hiddenFields.has("phone") ? null : doc.identity.phone,
        location: hiddenFields.has("location") ? null : doc.identity.location,
        links: hiddenFields.has("links") ? [] : doc.identity.links,
      }
    : doc.identity;

  const contactSeparator = " | ";
  const contacts = identityContactLines(visibleIdentity).map(escapeHtml).join(contactSeparator);
  const profile = language === "vi" ? "Tóm tắt" : "Professional Summary";
  const summary = doc.summary && !doc.summary.hidden ? `<section data-section-type="summary"><h2>${profile}</h2>${renderBlock(doc.summary)}</section>` : "";
  const sections = doc.sections
    .filter((section) => section.type !== "summary")
    .map((sec) => renderSection(sec))
    .join("");
  const header = `<header><h1>${escapeHtml(visibleIdentity.full_name || visibleIdentity.name || "CV")}</h1>${visibleIdentity.headline ? `<h3>${escapeHtml(visibleIdentity.headline)}</h3>` : ""}<p class="contacts">${contacts}</p></header>`;
  const body = `${summary}${sections}`;

  let customTypographyStyle = "";
  let pageMarginPx = 45; // Default ~12mm
  if (typography) {
    let basePt = 9.5;
    if (typeof typography.baseFontSize === "number" && !isNaN(typography.baseFontSize)) {
      basePt = typography.baseFontSize;
    } else if (typography.fontSize) {
      const parsed = parseFloat(typography.fontSize);
      if (!isNaN(parsed)) {
        basePt = typography.fontSize.includes("px") ? +(parsed * 0.75).toFixed(1) : parsed;
      }
    }

    const lh = typeof typography.lineHeight === "number"
      ? typography.lineHeight
      : (parseFloat(typography.lineHeight || "") || 1.4);
    const secGap = typeof typography.sectionSpacing === "number" ? typography.sectionSpacing : 4.0;
    const itemGap = typeof typography.itemSpacing === "number" ? typography.itemSpacing : 3.0;
    const pMargin = typeof typography.pageMargin === "number" ? typography.pageMargin : 12;
    pageMarginPx = Math.round(pMargin * 3.78);

    const fontRule = typography.fontFamily
      ? `font-family: ${typography.fontFamily}, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;`
      : "";

    customTypographyStyle = `<style>
      article.${design} {
        ${fontRule}
        padding: ${pMargin}mm !important;
      }
      article.${design} * {
        ${fontRule}
      }

      /* Proportional Typography Scale */
      article.${design} header h1 {
        font-size: ${(basePt * 2.1).toFixed(1)}pt !important;
      }
      article.${design} header h3 {
        font-size: ${(basePt * 1.15).toFixed(1)}pt !important;
      }
      article.${design} h2 {
        font-size: ${(basePt * 1.2).toFixed(1)}pt !important;
      }
      article.${design} .entry-title,
      article.${design} .entry-subtitle,
      article.${design} .entry-meta {
        font-size: ${(basePt * 1.0).toFixed(1)}pt !important;
      }
      article.${design} .item,
      article.${design} .bullet,
      article.${design} .skill-row,
      article.${design} .pub-row,
      article.${design} p,
      article.${design} span.skills {
        font-size: ${basePt.toFixed(1)}pt !important;
      }
      article.${design} .contacts {
        font-size: ${(basePt * 0.92).toFixed(1)}pt !important;
      }

      /* Granular Spacing Hierarchy */
      article.${design} section {
        margin-top: ${secGap}mm !important;
      }
      article.${design} .cv-entry,
      article.${design} .cv-education,
      article.${design} .skill-row,
      article.${design} .pub-row {
        margin-bottom: ${itemGap}mm !important;
      }
      article.${design} p,
      article.${design} .item,
      article.${design} .bullet,
      article.${design} .skill-row,
      article.${design} .pub-row,
      article.${design} .contacts,
      article.${design} .entry-header,
      article.${design} .entry-row-1,
      article.${design} .entry-row-2 {
        line-height: ${lh} !important;
      }

      /* Edge-to-edge page break separator with custom margin */
      article.${design} .cv-page-gap-wrapper {
        width: calc(100% + ${pMargin * 2}mm) !important;
        margin-left: -${pMargin}mm !important;
        margin-right: -${pMargin}mm !important;
      }
    </style>`;
  }

  const warning = design === "compact" && compactRenderingWarnings(doc).length
    ? ' data-render-warning="compact_template_content_exceeds_one_page"'
    : "";
  const paginationScript = `<script>
(function() {
  function applyPageBreaks() {
    var PAGE_H = 1123;
    var GAP_H = 52;
    var NEXT_PAD = ${pageMarginPx};
    var oldBreaks = document.querySelectorAll('.cv-page-break-container');
    for (var b = 0; b < oldBreaks.length; b++) {
      oldBreaks[b].remove();
    }
    var article = document.querySelector('article');
    if (!article) return;
    var candidates = article.querySelectorAll('section > h2, section > .cv-entry, section > .cv-education, section > .skill-row, section > .pub-row, section > p, section > div');
    if (!candidates.length) {
      candidates = article.querySelectorAll('h2, .cv-entry, .cv-education, .skill-row, .pub-row, p.bullet, p.item');
    }
    if (!candidates.length) return;

    var currentBreakTarget = PAGE_H;
    var pageNum = 2;

    for (var i = 0; i < candidates.length; i++) {
      var el = candidates[i];
      if (el.closest('.cv-page-break-container')) continue;

      var articleRect = article.getBoundingClientRect();
      var elRect = el.getBoundingClientRect();
      var elTop = elRect.top - articleRect.top;
      var elBottom = elRect.bottom - articleRect.top;

      var isHeader = el.tagName === 'H2';
      var nextBlock = isHeader ? el.nextElementSibling : null;
      var blockBottom = nextBlock ? (nextBlock.getBoundingClientRect().bottom - articleRect.top) : elBottom;
      var threshold = isHeader ? currentBreakTarget - 80 : currentBreakTarget - 10;

      if (elBottom > threshold || (isHeader && blockBottom > currentBreakTarget)) {
        var spacerH = Math.max(0, currentBreakTarget - elTop);
        var container = document.createElement('div');
        container.className = 'cv-page-break-container';
        container.innerHTML = '<div class="cv-page-end-spacer" style="height:' + spacerH + 'px; width:100%;"></div>' +
          '<div class="cv-page-gap-wrapper" style="height:' + GAP_H + 'px;">' +
            '<div class="cv-page-separator">' +
              '<span class="cv-page-separator-line"></span>' +
              '<span class="cv-page-separator-badge">Trang ' + pageNum + '</span>' +
              '<span class="cv-page-separator-line"></span>' +
            '</div>' +
          '</div>' +
          '<div class="cv-page-next-padding" style="height:' + NEXT_PAD + 'px; width:100%;"></div>';

        el.parentNode.insertBefore(container, el);

        articleRect = article.getBoundingClientRect();
        var newElRect = el.getBoundingClientRect();
        var newElTop = newElRect.top - articleRect.top;

        currentBreakTarget = newElTop + PAGE_H - NEXT_PAD;
        pageNum++;
      }
    }
    var totalPages = pageNum - 1;
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'CV_PAGE_COUNT', count: totalPages }, '*');
      }
    } catch (e) {}
  }

  window.applyPageBreaks = applyPageBreaks;
  if (document.readyState === 'complete') {
    applyPageBreaks();
  } else {
    window.addEventListener('load', applyPageBreaks);
  }
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function() {
      applyPageBreaks();
    });
  }
  setTimeout(applyPageBreaks, 60);
  setTimeout(applyPageBreaks, 250);
})();
</script>`;
  return `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style>${customTypographyStyle}</head><body${warning}><article class="${design}">${header}${body}</article>${paginationScript}</body></html>`;
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
  const title = (section.title || "").toLowerCase();
  if (
    section.type === "custom" &&
    (title.includes("unclassified") || title.includes("other content"))
  ) {
    return "";
  }
  const visibleBlocks = section.blocks.filter((block) => !block.hidden);
  if (visibleBlocks.length === 0) return "";
  return `<section data-section-type="${section.type}"><h2>${escapeHtml(section.title)}</h2>${visibleBlocks.map((b) => renderBlock(b)).join("")}</section>`;
}

function formatBulletText(text: string): string {
  const escaped = escapeHtml(text);
  return escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function renderBlock(block: CVBlockType): string {
  const confidence = block.confidence ?? (block.type === "unknown" ? 0 : 1);
  const attributes = `data-block-type="${block.type}" data-confidence="${confidence.toFixed(2)}"`;

  if (block.type === "entry") {
    const hasOrg = Boolean(block.organization);
    const hasLoc = Boolean(block.location);
    const hasDate = Boolean(block.date);
    const hasSub = Boolean(block.subtitle);

    let row1Left = "";
    let row1Right = "";
    let row2Left = "";
    let row2Right = "";

    if (hasOrg && hasLoc) {
      row1Left = `<span class="entry-title">${escapeHtml(block.organization!)}</span>`;
      row1Right = `<span class="entry-meta entry-location">${escapeHtml(block.location!)}</span>`;
      row2Left = `<span class="entry-subtitle"><em>${escapeHtml(block.title)}</em></span>` +
        (hasSub ? ` – <span>${escapeHtml(block.subtitle!)}</span>` : "");
      row2Right = hasDate ? `<span class="entry-meta entry-date"><em>${escapeHtml(block.date!)}</em></span>` : "";
    } else if (hasOrg) {
      row1Left = `<span class="entry-title">${escapeHtml(block.organization!)}</span>` +
        (block.title ? ` <span class="entry-separator">|</span> <span class="entry-subtitle"><em>${escapeHtml(block.title)}</em></span>` : "");
      row1Right = hasDate ? `<span class="entry-meta entry-date">${escapeHtml(block.date!)}</span>` : "";
      if (hasSub) {
        row2Left = `<span class="entry-subtitle"><em>${escapeHtml(block.subtitle!)}</em></span>`;
      }
    } else {
      row1Left = `<span class="entry-title">${escapeHtml(block.title)}</span>` +
        (hasSub ? ` <span class="entry-separator">|</span> <span class="entry-subtitle"><em>${escapeHtml(block.subtitle!)}</em></span>` : "");
      if (hasDate) {
        row1Right = `<span class="entry-meta entry-date">${escapeHtml(block.date!)}</span>`;
      } else if (hasLoc) {
        row1Right = `<span class="entry-meta entry-location">${escapeHtml(block.location!)}</span>`;
      }
      if (hasLoc && hasDate) {
        row2Right = `<span class="entry-meta entry-location"><em>${escapeHtml(block.location!)}</em></span>`;
      }
    }

    const row1Html = `<div class="entry-row-1"><div class="row-left">${row1Left}</div>${row1Right ? `<div class="row-right">${row1Right}</div>` : ""}</div>`;
    const row2Html = (row2Left || row2Right)
      ? `<div class="entry-row-2"><div class="row-left">${row2Left}</div>${row2Right ? `<div class="row-right">${row2Right}</div>` : ""}</div>`
      : "";

    const bulletsHtml = block.bullets.length
      ? `<ul class="bullet-list">${block.bullets.map((bullet) => `<li class="bullet">${formatBulletText(bullet)}</li>`).join("")}</ul>`
      : "";

    return `<div class="cv-entry" ${attributes}><div class="entry-header">${row1Html}${row2Html}</div>${bulletsHtml}</div>`;
  }

  if (block.type === "bullet") return `<p class="bullet" ${attributes}>${formatBulletText(block.text)}</p>`;
  if (block.type === "paragraph") return `<p class="item" ${attributes}>${formatBulletText(block.text)}</p>`;

  if (block.type === "skill_group") {
    const labelHtml = block.label ? `<strong class="skills-label">${escapeHtml(block.label)}: </strong>` : "";
    const skillsHtml = `<span class="skills">${block.skills.map(escapeHtml).join(", ")}</span>`;
    return `<div class="skill-row" ${attributes}><span class="bullet-char">• </span>${labelHtml}${skillsHtml}</div>`;
  }

  if (block.type === "publication") {
    const authors = block.authors ? `<span class="pub-authors">${escapeHtml(block.authors)}. </span>` : "";
    const title = block.title ? `<span class="pub-title">“${escapeHtml(block.title)}” </span>` : "";
    const venue = block.venue ? `<em class="pub-venue">${escapeHtml(block.venue)}</em>` : "";
    const status = block.status ? `<span class="pub-status">${escapeHtml(block.status)}</span>` : "";
    const date = block.date ? `<span class="pub-date">${escapeHtml(block.date)}</span>` : "";

    const metaParts = [venue, status, date].filter(Boolean);
    const metaHtml = metaParts.length ? metaParts.join(", ") : "";

    return `<div class="pub-row" ${attributes}><span class="bullet-char">• </span>${authors}${title}${metaHtml}</div>`;
  }

  if (block.type === "education") {
    const inst = block.institution ? `<span class="entry-title">${escapeHtml(block.institution)}</span>` : "";
    const loc = block.location ? `<span class="entry-meta entry-location">${escapeHtml(block.location)}</span>` : "";

    const degParts = [block.degree, block.field].filter(isPresent).map(escapeHtml);
    const degreeHtml = degParts.length ? `<span class="entry-subtitle"><em>${degParts.join(" in ")}</em></span>` : "";
    const dateHtml = block.date ? `<span class="entry-meta entry-date"><em>${escapeHtml(block.date)}</em></span>` : "";

    const row1 = `<div class="entry-row-1"><div class="row-left">${inst}</div>${loc ? `<div class="row-right">${loc}</div>` : ""}</div>`;
    const row2 = (degreeHtml || dateHtml)
      ? `<div class="entry-row-2"><div class="row-left">${degreeHtml}</div>${dateHtml ? `<div class="row-right">${dateHtml}</div>` : ""}</div>`
      : "";

    const detailsHtml = block.details && block.details.length
      ? `<div class="education-details">${block.details.map((d) => `<p class="item edu-detail">${formatBulletText(d)}</p>`).join("")}</div>`
      : "";

    return `<div class="cv-education" ${attributes}><div class="entry-header">${row1}${row2}</div>${detailsHtml}</div>`;
  }

  return `<p class="item unknown" ${attributes}>${escapeHtml(block.lines.join(" | "))}</p>`;
}

function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function isPresent(value: string | null | undefined): value is string { return Boolean(value); }

const CSS = `
@page { size: A4; margin: 0; } * { box-sizing: border-box; }
html, body { margin: 0; padding: 0; color: #111827; font-family: Arial, sans-serif; background: #ffffff; overflow: hidden; }
article { width: 210mm; min-height: 297mm; background: #ffffff; padding: 16mm; margin: 0 auto; box-sizing: border-box; }
.cv-page-break-container { display: block; width: 100%; clear: both; }
.cv-page-end-spacer { display: block; width: 100%; background: #ffffff; }
.cv-page-gap-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: calc(100% + 32mm);
  margin-left: -16mm;
  margin-right: -16mm;
  height: 52px;
  background: #F1F5F9;
  border-top: 2px dashed #94A3B8;
  border-bottom: 2px dashed #94A3B8;
  position: relative;
  user-select: none;
  box-sizing: border-box;
}
.cv-page-separator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  gap: 16px;
  padding: 0 24px;
}
.cv-page-separator-line {
  flex: 1;
  height: 1px;
  background: #CBD5E1;
}
.cv-page-separator-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #FFFFFF;
  border: 1.5px solid #64748B;
  border-radius: 9999px;
  padding: 4px 16px;
  font-size: 11px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-weight: 700;
  color: #1E293B;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}
.cv-page-next-padding { display: block; height: 16mm; width: 100%; background: #ffffff; }
@media print {
  body { background: white !important; }
  article { box-shadow: none !important; border: none !important; margin: 0 !important; width: auto !important; min-height: auto !important; }
  .cv-page-break-container { display: none !important; }
}
header { border-bottom: 1px solid #9ca3af; padding-bottom: 5mm; }
h1 { margin: 0 0 1mm; font-size: 24pt; } h3 { margin: 0 0 3mm; font-size: 11pt; }
.contacts { color: #596565; font-size: 8.5pt; } section { margin-top: 6mm; break-inside: avoid; }
h2 { margin: 0 0 2.5mm; border-bottom: 1px solid #9ca3af; padding-bottom: 1mm; font-size: 10pt; text-transform: uppercase; letter-spacing: 1.2px; }
.item, .bullet, .entry-title, .entry-subtitle, .entry-meta { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; white-space: pre-wrap; }
.entry-title { font-weight: 700; } .entry-subtitle, .entry-meta { color: #555; }
.bullet { padding-left: 4mm; } .bullet::before { content: '\\2022'; margin-left: -3mm; margin-right: 2mm; }
.skills { font-size: 8.5pt; color: #333; } .publication { font-size: 9pt; font-style: italic; }
.unknown, .neutral-block { font-weight: 400; font-style: normal; }

/* ── Classic ATS (Reference Harvard / LaTeX Design) ── */
.classic_ats {
  font-family: "Times New Roman", Times, "Liberation Serif", Georgia, serif;
  color: #000000;
  padding: 12mm 12mm;
  line-height: 1.4;
  font-size: 9.5pt;
  background: #ffffff;
}
.classic_ats header {
  text-align: center;
  border-bottom: none;
  padding-bottom: 2mm;
  margin-bottom: 2mm;
}
.classic_ats header h1 {
  font-size: 21pt;
  font-weight: 700;
  margin: 0 0 1.5mm 0;
  color: #000000;
  letter-spacing: 0.2px;
  text-transform: none;
}
.classic_ats header h3 {
  font-size: 11pt;
  font-weight: 600;
  margin: 0 0 2mm 0;
  color: #000000;
}
.classic_ats .contacts {
  font-size: 9pt;
  color: #000000;
  margin: 0;
  line-height: 1.35;
}
.classic_ats section {
  margin-top: 4mm;
  margin-bottom: 0;
  break-inside: avoid;
  page-break-inside: avoid;
}
.classic_ats h2 {
  font-size: 11.5pt;
  font-weight: 700;
  color: #000000;
  border-bottom: 1px solid #000000;
  padding-bottom: 1px;
  margin: 0 0 2.5mm 0;
  letter-spacing: 0.2px;
  text-transform: none;
}
.classic_ats .item {
  font-size: 9.5pt;
  line-height: 1.38;
  color: #000000;
  margin: 0 0 2mm 0;
  text-align: justify;
}
.classic_ats .cv-entry,
.classic_ats .cv-education {
  margin-bottom: 3mm;
  break-inside: avoid;
  page-break-inside: avoid;
}
.classic_ats .entry-header {
  margin-bottom: 1.5mm;
}
.classic_ats .entry-row-1,
.classic_ats .entry-row-2 {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  width: 100%;
  line-height: 1.35;
}
.classic_ats .row-left {
  display: flex;
  align-items: baseline;
  gap: 0.35em;
  flex-wrap: wrap;
  flex: 1 1 auto;
  min-width: 0;
}
.classic_ats .row-right {
  text-align: right;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: 1em;
}
.classic_ats .entry-separator {
  color: #000000;
  font-weight: 400;
  padding: 0 1px;
}
.classic_ats .entry-title {
  font-size: 9.8pt;
  font-weight: 700;
  color: #000000;
  margin: 0;
}
.classic_ats .entry-subtitle {
  font-size: 9.5pt;
  color: #000000;
  margin: 0;
}
.classic_ats .entry-location,
.classic_ats .entry-date,
.classic_ats .entry-meta {
  font-size: 9.2pt;
  color: #000000;
  text-align: right;
  white-space: nowrap;
  margin: 0;
}
.classic_ats .entry-location em,
.classic_ats .entry-date em,
.classic_ats .entry-meta em {
  font-style: italic;
}
.classic_ats .bullet-list {
  margin: 1mm 0 2mm 0;
  padding-left: 5mm;
  list-style-type: disc;
}
.classic_ats .bullet {
  font-size: 9.3pt;
  line-height: 1.38;
  color: #000000;
  margin: 0 0 1.2mm 0;
  text-align: justify;
  padding-left: 0;
}
.classic_ats .bullet::before {
  content: none;
}
.classic_ats .skill-row {
  font-size: 9.3pt;
  line-height: 1.38;
  margin-bottom: 1.5mm;
  color: #000000;
  text-align: justify;
}
.classic_ats .skills-label {
  font-weight: 700;
  color: #000000;
}
.classic_ats .skills {
  color: #000000;
}
.classic_ats .bullet-char {
  display: inline-block;
  width: 4mm;
  font-weight: 700;
}
.classic_ats .pub-row {
  font-size: 9.3pt;
  line-height: 1.38;
  margin-bottom: 1.8mm;
  color: #000000;
  text-align: justify;
}
.classic_ats .education-details {
  margin-top: 1mm;
  margin-bottom: 2mm;
}
.classic_ats .edu-detail {
  font-size: 9.3pt;
  line-height: 1.35;
  margin: 0 0 1mm 0;
}

/* ── Compact (Single-Column ATS, High Density) ── */
/* Same structural rules as Classic ATS: single column, 2-row entry headers,
   categorized skill bullets, clean citations. Teal accent (#4A90A4) and
   tighter spacing distinguish it; nothing sidebar/flex (ATS-safe). */
.compact_one_page, .compact {
  font-family: Arial, Helvetica, sans-serif;
  color: #111827;
  padding: 10mm 13mm;
  line-height: 1.35;
  font-size: 8.5pt;
  background: #ffffff;
}
.compact_one_page header, .compact header {
  text-align: left;
  border-bottom: none;
  border-top: 1.5mm solid #4A90A4;
  padding-top: 2mm;
  padding-bottom: 2mm;
  margin-bottom: 2mm;
}
.compact_one_page header h1, .compact header h1 {
  font-size: 16pt;
  font-weight: 700;
  margin: 0 0 1mm 0;
  color: #111827;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.compact_one_page header h3, .compact header h3 {
  font-size: 9.5pt;
  font-weight: 600;
  margin: 0 0 1.5mm 0;
  color: #374151;
}
.compact_one_page .contacts, .compact .contacts {
  font-size: 8pt;
  color: #4b5563;
  margin: 0;
  line-height: 1.35;
}
.compact_one_page section, .compact section {
  margin-top: 3.5mm;
  margin-bottom: 0;
  break-inside: avoid;
  page-break-inside: avoid;
}
.compact_one_page h2, .compact h2 {
  font-size: 9.5pt;
  font-weight: 700;
  color: #111827;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 0;
  border-left: 1mm solid #4A90A4;
  padding-left: 2mm;
  padding-bottom: 1px;
  margin: 0 0 2mm 0;
}
.compact_one_page .item, .compact .item {
  font-size: 8.5pt;
  line-height: 1.35;
  color: #111827;
  margin: 0 0 1.5mm 0;
  text-align: left;
}
.compact_one_page .cv-entry, .compact .cv-entry,
.compact_one_page .cv-education, .compact .cv-education {
  margin-bottom: 2mm;
  break-inside: avoid;
  page-break-inside: avoid;
}
.compact_one_page .entry-header, .compact .entry-header {
  margin-bottom: 1mm;
}
.compact_one_page .entry-row-1, .compact .entry-row-1,
.compact_one_page .entry-row-2, .compact .entry-row-2 {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  width: 100%;
  line-height: 1.3;
}
.compact_one_page .row-left, .compact .row-left {
  display: flex;
  align-items: baseline;
  gap: 0.35em;
  flex-wrap: wrap;
  flex: 1 1 auto;
  min-width: 0;
}
.compact_one_page .row-right, .compact .row-right {
  text-align: right;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: 1em;
}
.compact_one_page .entry-separator, .compact .entry-separator {
  color: #111827;
  font-weight: 400;
  padding: 0 1px;
}
.compact_one_page .entry-title, .compact .entry-title {
  font-size: 9pt;
  font-weight: 700;
  color: #111827;
  margin: 0;
}
.compact_one_page .entry-subtitle, .compact .entry-subtitle {
  font-size: 8.5pt;
  color: #374151;
  margin: 0;
}
.compact_one_page .entry-location, .compact .entry-location,
.compact_one_page .entry-date, .compact .entry-date,
.compact_one_page .entry-meta, .compact .entry-meta {
  font-size: 8pt;
  color: #6b7280;
  text-align: right;
  white-space: nowrap;
  margin: 0;
}
.compact_one_page .entry-location em, .compact .entry-location em,
.compact_one_page .entry-date em, .compact .entry-date em,
.compact_one_page .entry-meta em, .compact .entry-meta em {
  font-style: italic;
}
.compact_one_page .bullet-list, .compact .bullet-list {
  margin: 1mm 0 1.5mm 0;
  padding-left: 5mm;
  list-style-type: disc;
}
.compact_one_page .bullet, .compact .bullet {
  font-size: 8.5pt;
  line-height: 1.3;
  color: #111827;
  margin: 0 0 1mm 0;
  padding-left: 0;
}
.compact_one_page .bullet::before, .compact .bullet::before {
  content: none;
}
.compact_one_page .skill-row, .compact .skill-row {
  font-size: 8.5pt;
  line-height: 1.3;
  margin-bottom: 1mm;
  color: #111827;
}
.compact_one_page .skills-label, .compact .skills-label {
  font-weight: 700;
  color: #111827;
}
.compact_one_page .skills, .compact .skills {
  color: #111827;
}
.compact_one_page .bullet-char, .compact .bullet-char {
  display: inline-block;
  width: 4mm;
  font-weight: 700;
}
.compact_one_page .pub-row, .compact .pub-row {
  font-size: 8.5pt;
  line-height: 1.3;
  margin-bottom: 1.2mm;
  color: #111827;
}
.compact_one_page .education-details, .compact .education-details {
  margin-top: 1mm;
  margin-bottom: 1.5mm;
}
.compact_one_page .edu-detail, .compact .edu-detail {
  font-size: 8.5pt;
  line-height: 1.3;
  margin: 0 0 1mm 0;
}
`;
