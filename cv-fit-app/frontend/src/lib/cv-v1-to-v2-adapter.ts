/**
 * V1 → V2 Compatibility Adapter (frontend)
 *
 * Converts the legacy TailoredCV model (sections[].items: string[]) into a
 * CVDocumentV2-compatible shape so the V2 renderer can display legacy CVs.
 *
 * Rules
 * ------
 * - Recognized bullets → bullet blocks (inside entry blocks when preceded by
 *   an entry headline, or as standalone bullet blocks).
 * - Clearly recognized entry titles → entry blocks.
 * - Uncertain non-bullet content → paragraph or unknown block.
 * - Never highlight uncertain content.
 * - Never discard content.
 */

import type {
  CVBlockType,
  CVDocumentV2,
  CVSkillGroupBlock,
  CVPublicationBlock,
  CVSection,
  CVIdentity,
} from "@/types";
import { parseLegacyContactLines } from "./cv-identity-compat.js";

// ---------------------------------------------------------------------------
// Section-type heuristics
// ---------------------------------------------------------------------------

const EXPERIENCE_KEYS = [
  "work experience", "experience", "professional experience",
  "employment history", "work history", "career history",
  "kinh nghiem", "kinh nghiem lam viec", "kinh nghem",
  "qua trinh lam viec", "lich su lam viec",
];

const PROJECTS_KEYS = [
  "projects", "personal projects", "academic projects",
  "du an", "du an ca nhan", "cac du an", "kinh nghiem du an",
];

const SKILLS_KEYS = [
  "technical skills", "skills", "key skills", "core competencies",
  "ky nang", "ky nang chuyen mon", "ky nang mem", "cong nghe su dung",
  "cong nghe",
];

const EDUCATION_KEYS = [
  "education", "education & certifications", "hoc van",
  "trinh do hoc van", "bang cap", "qua trinh hoc tap",
];

const PUBLICATIONS_KEYS = ["publications", "cong bo khoa hoc"];

const CERTIFICATIONS_KEYS = [
  "certifications", "certificates", "professional certifications",
  "chung chi", "chung chi nghe nghiep", "chung nhan",
];

const LANGUAGES_KEYS = ["languages", "ngoai ngu", "ngon ngu"];

const SUMMARY_KEYS = [
  "summary", "professional summary", "profile", "about me",
  "tom tat", "gioi thieu", "muc tieu nghe nghiep",
];

const OTHER_KEYS = [
  "awards", "giai thuong", "thanh tuu",
  "volunteering", "hoat dong", "hoat dong xa hoi", "hoat dong tinh nguyen",
  "activities", "interests", "hobbies", "lien he", "contact",
  "contact information", "thong tin ca nhan", "thong tin lien he", "so luoc",
  "additional information",
];

function normalizeHeading(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[:\s]+$/, "");
}

function classifySection(title: string): CVSection["type"] {
  const n = normalizeHeading(title);
  if (SUMMARY_KEYS.includes(n)) return "summary";
  if (EXPERIENCE_KEYS.includes(n)) return "experience";
  if (PROJECTS_KEYS.includes(n)) return "projects";
  if (SKILLS_KEYS.includes(n)) return "skills";
  if (EDUCATION_KEYS.includes(n)) return "education";
  if (PUBLICATIONS_KEYS.includes(n)) return "publications";
  if (CERTIFICATIONS_KEYS.includes(n)) return "certifications";
  if (LANGUAGES_KEYS.includes(n)) return "languages";
  if (OTHER_KEYS.some((key) => n.includes(key))) {
    if (n.includes("award") || n.includes("thanh tuu")) return "awards";
    if (n.includes("hoat dong") || n.includes("volunteer")) return "activities";
    if (n.includes("interest") || n.includes("hobby")) return "interests";
  }
  return "custom";
}

// ---------------------------------------------------------------------------
// Entry detection
// ---------------------------------------------------------------------------

const ROLE_TOKENS = [
  "engineer", "developer", "designer", "manager", "lead", "analyst",
  "consultant", "ky su", "lap trinh vien", "chuyen vien", "quan ly",
  "intern", "fresher", "junior", "senior", "specialist", "director",
  "vp", "ceo", "cto", "cfo", "co founder", "founder",
  "teacher", "gia su", "nhan vien", "truong",
  "scientist", "researcher", "architect", "plumber", "nurse",
];

function isEntryHeadline(item: string): boolean {
  const stripped = item.replace(/^[•●▪◦]\s*/, "").trim();
  if (!stripped || stripped[0] === stripped[0].toLowerCase()) return false;
  if (/[.!?;:]$/.test(stripped)) return false;
  const lower = stripped.toLowerCase();
  if (/\b(20|19)\d{2}\b/.test(lower)) return true;
  if (ROLE_TOKENS.some((t) => new RegExp(`\\b${t}\\b`).test(lower))) return true;
  if (/[—–]\s*[A-Z]/.test(stripped) || / \/\s*[A-Z]/.test(stripped)) return true;
  return false;
}

const EDUCATION_HEADLINE_TOKENS = [
  "university", "college", "school", "institute", "academy",
  "dai hoc", "cao dang", "hoc vien", "truong",
];

const EDUCATION_NAME_CONNECTORS = new Set([
  "of", "the", "and", "for", "in",
  "dai", "hoc", "cao", "dang", "vien", "truong",
]);

function isEducationHeadline(item: string): boolean {
  const stripped = item.trim();
  if (!stripped || /[.!?;:]$/.test(stripped)) return false;
  const candidate = stripped
    .replace(/\s*(?:[—–|-]\s*)?(?:19|20)\d{2}(?:\s*[—–-]\s*(?:19|20)\d{2})?.*$/, "")
    .replace(/^[\s—–|-]+|[\s—–|-]+$/g, "");
  const normalized = normalizeHeading(candidate);
  if (!EDUCATION_HEADLINE_TOKENS.some((token) =>
    new RegExp(`\\b${token}\\b`).test(normalized))) return false;
  const words = candidate.match(/[\p{L}]+/gu) || [];
  return words.length > 0 && words.every((word) =>
    EDUCATION_NAME_CONNECTORS.has(normalizeHeading(word))
      || word[0] === word[0].toUpperCase(),
  );
}

// ---------------------------------------------------------------------------
// Skill group detection
// ---------------------------------------------------------------------------

function looksLikeSkillGroup(
  item: string,
): [true, { label: string; skills: string[] }] | [false, null] {
  const match = item.match(/^([A-ZÀ-Ỹa-zà-ỹ][^\r\n:]{1,30})\s*:\s*(.+)$/);
  if (!match) return [false, null];
  const [, label, skillsRaw] = match;
  const parts = skillsRaw
    .split(/[,;·&]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (parts.length < 2 || parts.length > 12) return [false, null];
  return [true, { label: label.trim(), skills: parts }];
}

// ---------------------------------------------------------------------------
// Line continuation
// ---------------------------------------------------------------------------

function normalizeItems(items: string[]): string[] {
  const normalized: string[] = [];
  for (const item of items) {
    const stripped = item.trim();
    if (!stripped) continue;
    const prev = normalized.at(-1);
    if (prev && /^[•●▪◦]/.test(prev) && stripped && /^[\p{Ll}]/u.test(stripped)) {
      normalized[normalized.length - 1] = `${prev.trimEnd()} ${stripped}`;
    } else {
      normalized.push(item);
    }
  }
  return normalized;
}

// ---------------------------------------------------------------------------
// Section parsers
// ---------------------------------------------------------------------------

function parseSkillSection(items: string[]): CVBlockType[] {
  const groups: CVSkillGroupBlock[] = [];
  const loose: string[] = [];
  for (const item of items) {
    const [isGroup, info] = looksLikeSkillGroup(item);
    if (isGroup) groups.push({ type: "skill_group", block_id: "", label: info.label, skills: info.skills });
    else {
      const cleaned = item.replace(/^[•●▪◦]\s*/, "").trim();
      if (cleaned) loose.push(cleaned);
    }
  }
  if (groups.length) {
    if (loose.length) groups.push({ type: "skill_group", block_id: "", skills: loose });
    return groups;
  }
  return loose.length
    ? [{ type: "skill_group", block_id: "", skills: loose }]
    : [{ type: "paragraph", block_id: "", text: items.join(" ") }];
}

function parseGeneralSection(items: string[], isSummary: boolean): CVBlockType[] {
  if (isSummary) return [{ type: "paragraph", block_id: "", text: items.join(" ") }];

  const blocks: CVBlockType[] = [];
  let currentEntry: string[] = [];

  for (const item of items) {
    const isBullet = /^[•●▪◦]/.test(item);
    const cleaned = item.replace(/^[•●▪◦]\s*/, "").trim();
    if (!cleaned) continue;

    if (isEntryHeadline(cleaned)) {
      if (currentEntry.length) {
        const [bullets, extra] = splitBullets(currentEntry);
        blocks.push({
          type: "entry",
          block_id: "",
          title: extra.join(" "),
          bullets: bullets.map((b) => b.replace(/^[•●▪◦]\s*/, "")),
        });
      }
      currentEntry = [cleaned];
    } else if (isBullet) {
      if (currentEntry.length) currentEntry.push(item);
      else blocks.push({ type: "bullet", block_id: "", text: cleaned });
    } else if (currentEntry.length) {
      currentEntry.push(cleaned);
    } else {
      blocks.push({ type: "paragraph", block_id: "", text: cleaned });
    }
  }

  if (currentEntry.length) {
    const [bullets, extra] = splitBullets(currentEntry);
    blocks.push({
      type: "entry",
      block_id: "",
      title: extra.join(" "),
      bullets: bullets.map((b) => b.replace(/^[•●▪◦]\s*/, "")),
    });
  }

  return blocks.length ? blocks : [{ type: "paragraph", block_id: "", text: items.join(" ") }];
}

function parseEducationSection(items: string[]): CVBlockType[] {
  const cleanedItems = items
    .map((item) => item.replace(/^[•●▪◦]\s*/, "").trim())
    .filter(Boolean);
  const blocks: CVBlockType[] = [];
  let institution: string | undefined;
  let details: string[] = [];
  const flush = () => {
    if (institution || details.length) {
      blocks.push({ type: "education", block_id: "", institution, details });
    }
    institution = undefined;
    details = [];
  };
  for (const item of cleanedItems) {
    if (isEducationHeadline(item)) {
      flush();
      institution = item;
    } else {
      details.push(item);
    }
  }
  flush();
  return blocks;
}

function splitBullets(lines: string[]): [string[], string[]] {
  const bullets: string[] = [];
  const headline: string[] = [];
  for (const line of lines) {
    const isBullet = /^[•●▪◦]/.test(line);
    const cleaned = line.replace(/^[•●▪◦]\s*/, "").trim();
    if (!cleaned) continue;
    if (isBullet) bullets.push(line);
    else if (headline.length && isEntryHeadline(cleaned)) headline.push(cleaned);
    else if (!headline.length && !bullets.length) headline.push(cleaned);
    else if (bullets.length) bullets.push(cleaned);
    else headline.push(cleaned);
  }
  return [bullets, headline];
}

// ---------------------------------------------------------------------------
// Public adapter
// ---------------------------------------------------------------------------

function legacyIdentity(name: string, headline?: string, contactLines?: string[]): CVIdentity {
  const contacts = (contactLines || []).map((line) => line.trim()).filter(Boolean);
  const parsed = parseLegacyContactLines(contacts);
  const normalizedContacts = [parsed.email, parsed.phone, ...parsed.links, ...parsed.residual]
    .filter((value): value is string => Boolean(value))
    .filter((value, index, all) => all.indexOf(value) === index);
  const fullName = name.trim() || null;

  return {
    full_name: fullName,
    headline: headline?.trim() || null,
    email: parsed.email,
    phone: parsed.phone,
    location: null,
    links: parsed.links,
    source_block_ids: [],
    field_source_block_ids: {
      full_name: [],
      headline: [],
      email: [],
      phone: [],
      location: [],
      links: {},
    },
    name: fullName ?? "",
    contact_lines: normalizedContacts,
  };
}

export function v1ToV2(
  name: string,
  headline?: string,
  contactLines?: string[],
  summary?: string,
  sections?: { title: string; items: string[] }[],
  experience?: { company: string; role: string; bullet_points: string[] }[],
  skills?: string[],
  education?: string,
): CVDocumentV2 {
  const identity = legacyIdentity(name, headline, contactLines);

  const summaryParts = summary?.trim() ? [summary.trim()] : [];
  for (const section of sections || []) {
    if (classifySection(section.title) !== "summary") continue;
    const sectionSummary = normalizeItems(section.items).join(" ").trim();
    if (sectionSummary && !summaryParts.includes(sectionSummary)) summaryParts.push(sectionSummary);
  }
  const summaryBlock = summaryParts.length
    ? { type: "paragraph" as const, block_id: "v1-summary", text: summaryParts.join("\n") }
    : undefined;

  const cvSections: CVSection[] = [];
  for (const section of sections || []) {
    if (!section.title && !section.items?.length) continue;
    const type = classifySection(section.title);
    if (type === "summary") continue;
    const blocks = _sectionToBlocks(section, type);
    cvSections.push({
      id: "",
      type,
      title: section.title,
      confidence: 1,
      source_block_ids: [],
      blocks,
    });
  }

  // Fallback: derive from legacy fields
  if (!cvSections.length) {
    if (experience) {
      cvSections.push({
        id: "experience",
        type: "experience",
        title: "Experience",
        confidence: 1,
        source_block_ids: [],
        blocks: experience.map((exp) => ({
          type: "entry" as const,
          block_id: "",
          title: [exp.role, exp.company].filter(Boolean).join(" — "),
          bullets: exp.bullet_points.map((b) => b.replace(/^[•●▪◦]\s*/, "")),
        })),
      });
    }
    if (skills?.length) {
      cvSections.push({
        id: "skills",
        type: "skills",
        title: "Skills",
        confidence: 1,
        source_block_ids: [],
        blocks: [{ type: "skill_group" as const, block_id: "", skills }],
      });
    }
    if (education?.trim()) {
      cvSections.push({
        id: "education",
        type: "education",
        title: "Education",
        confidence: 1,
        source_block_ids: [],
        blocks: [{ type: "education" as const, block_id: "", details: [education.trim()] }],
      });
    }
  }

  cvSections.forEach((section, sectionIndex) => {
    section.id = `v1-section-${sectionIndex}`;
    section.blocks.forEach((block, blockIndex) => {
      block.block_id = `${section.id}-block-${blockIndex}`;
    });
  });

  return {
    raw_extraction_id: null,
    schema_version: 2,
    extraction_version: "2.0",
    parser_version: "2.0",
    reconstruction_version: 1,
    requires_reprocessing: true,
    source_hash: null,
    identity,
    summary: summaryBlock ?? null,
    sections: cvSections,
    unmapped_content: [],
    reconstruction_warnings: [],
  };
}

function _sectionToBlocks(section: { title: string; items: string[] }, type: string): CVBlockType[] {
  const items = normalizeItems(section.items);
  if (type === "skills") return parseSkillSection(items);
  if (type === "education") return parseEducationSection(items);
  if (type === "publications") {
    const pubs: CVPublicationBlock[] = [];
    const current: string[] = [];
    for (const item of items) {
      const c = item.replace(/^[•●▪◦]\s*/, "").trim();
      if (!c) continue;
      if (current.length && isEntryHeadline(c)) {
        pubs.push({ type: "publication", block_id: "", title: current.join(" ") });
        current.length = 0;
      }
      current.push(c);
    }
    if (current.length) pubs.push({ type: "publication", block_id: "", title: current.join(" ") });
    return pubs.length ? pubs : [{ type: "paragraph", block_id: "", text: items.join(" ") }];
  }
  return parseGeneralSection(items, type === "summary");
}
