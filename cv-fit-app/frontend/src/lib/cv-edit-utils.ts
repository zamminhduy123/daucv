// ── Edit-only wizard helpers ──────────────────────────────────────────────────
//
// Pure helpers for the /app/review editor page: deep cloning CVDocumentV2
// drafts, stamping user edits with their ContentOrigin, and producing the
// canonical contact lines used by the identity form.

import type {
  CVBlock,
  CVBlockMetadata,
  CVDocumentV2,
  CVEntryBlock,
  CVIdentity,
  CVParagraphBlock,
} from "@/types";
import { CURRENT_RECONSTRUCTION_VERSION } from "@/types";

export function normalizeSkillsBlocks(blocks: CVBlock[]): CVBlock[] {
  const result: CVBlock[] = [];
  for (const block of blocks) {
    if (block.type === "skill_group") {
      result.push(block);
      continue;
    }
    const text = (block.type === "bullet" || block.type === "paragraph") ? block.text?.trim() : "";
    if (!text) {
      result.push(block);
      continue;
    }
    // Strip leading bullet markers: •, ●, ▪, ▫, ►, ‣, –, —, -, *
    const cleanText = text.replace(/^[\u2022\u25CF\u25AA\u25AB\u25BA\u2043\u2013\u2014\-*]\s*/, "").trim();
    if (cleanText.includes(":")) {
      const colonIdx = cleanText.indexOf(":");
      const label = cleanText.substring(0, colonIdx).trim();
      const rest = cleanText.substring(colonIdx + 1).trim();
      const skills = rest
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      result.push({
        ...block,
        type: "skill_group",
        label,
        skills,
      } as unknown as CVBlock);
    } else {
      const last = result[result.length - 1];
      if (last && last.type === "skill_group" && (last as unknown as { skills?: string[] }).skills && (last as unknown as { skills: string[] }).skills.length > 0) {
        if (!cleanText.includes(",") && cleanText.split(/\s+/).length <= 4) {
          const skillsArr = (last as unknown as { skills: string[] }).skills;
          skillsArr[skillsArr.length - 1] = `${skillsArr[skillsArr.length - 1]} ${cleanText}`.trim();
          continue;
        }
      }
      const skills = cleanText
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (skills.length > 1) {
        result.push({
          ...block,
          type: "skill_group",
          label: undefined,
          skills,
        } as unknown as CVBlock);
      } else {
        result.push(block);
      }
    }
  }
  return result;
}

export function isSuppressedCustomSection(section: { type: string; title?: string | null }): boolean {
  const t = (section.title || "").toLowerCase().trim();
  return (
    section.type === "custom" &&
    (t.includes("unclassified") || t.includes("other content"))
  );
}

const CERT_KNOWN_ISSUERS = [
  "ibm",
  "deeplearning.ai",
  "deeplearning",
  "mathworks",
  "coursera",
  "udemy",
  "edx",
  "google",
  "microsoft",
  "oracle",
  "cisco",
  "meta",
  "linkedin",
  "aws",
  "amazon",
];

const DATE_LINE_REGEX =
  /^(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2}\/\d{1,2}\/\d{2,4}|\d{4})\b.*|\d{4}\s*[-–—]\s*(?:\d{4}|present|current)|(?:present|current))$/i;

const EXTRACT_DATE_REGEX =
  /(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2}\/\d{1,2}\/\d{2,4}|\d{4})(?:\s*[-–—]\s*(?:\d{4}|present|current))?/i;

function isPureDateString(str: string): boolean {
  const trimmed = str.trim();
  if (!trimmed || trimmed.length > 30) return false;
  return DATE_LINE_REGEX.test(trimmed);
}

export function normalizeCertificationsBlocks(blocks: CVBlock[]): CVBlock[] {
  const result: CVBlock[] = [];

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];

    // Check if this block is an orphan date (e.g. entry with title=date, or bullet/paragraph containing just a date)
    let isDateOnly = false;
    let extractedDate = "";

    if (block.type === "entry") {
      const title = block.title?.trim() || "";
      const date = block.date?.trim() || "";
      if (isPureDateString(title) || (title === date && isPureDateString(date))) {
        isDateOnly = true;
        extractedDate = date || title;
      }
    } else if (block.type === "paragraph" || block.type === "bullet") {
      const text = (block.text || "")
        .replace(/^[\u2022\u25CF\u25AA\u25AB\u25BA\u2043\u2013\u2014\-*]\s*/, "")
        .trim();
      if (isPureDateString(text)) {
        isDateOnly = true;
        extractedDate = text;
      }
    }

    if (isDateOnly) {
      // If we have a preceding entry in result, bind this date to it and skip this block!
      const prev = result[result.length - 1];
      if (prev && prev.type === "entry") {
        if (!prev.date) {
          prev.date = extractedDate;
        }
        continue;
      }
    }

    // If it's an entry block:
    if (block.type === "entry") {
      let org = block.organization?.trim() || "";
      let title = block.title?.trim() || "";
      let date = block.date?.trim() || "";

      // If org is missing but title contains '|' or ' - '
      if (!org && title) {
        if (title.includes("|")) {
          const parts = title.split("|").map((p) => p.trim()).filter(Boolean);
          if (parts.length > 1) {
            const p0Lower = parts[0].toLowerCase();
            if (CERT_KNOWN_ISSUERS.some((ki) => p0Lower.includes(ki))) {
              org = parts[0];
              title = parts.slice(1).join(" | ");
            } else {
              title = parts[0];
              org = parts.slice(1).join(" | ");
            }
          }
        } else if (/\s+[—–-]\s+/.test(title)) {
          const parts = title.split(/\s+[—–-]\s+/).map((p) => p.trim()).filter(Boolean);
          if (parts.length > 1) {
            const p0Lower = parts[0].toLowerCase();
            if (CERT_KNOWN_ISSUERS.some((ki) => p0Lower.includes(ki))) {
              org = parts[0];
              title = parts.slice(1).join(" - ");
            } else {
              title = parts[0];
              org = parts.slice(1).join(" - ");
            }
          }
        }
      }

      // If date is still missing, check if title has an embedded date at the end
      if (!date && title) {
        const dMatch = title.match(EXTRACT_DATE_REGEX);
        if (dMatch && (title.endsWith(`(${dMatch[0]})`) || title.endsWith(dMatch[0]))) {
          date = dMatch[0];
          title = title
            .replace(`(${dMatch[0]})`, "")
            .replace(dMatch[0], "")
            .trim()
            .replace(/[-–—|]$/, "")
            .trim();
        }
      }

      result.push({
        ...block,
        title,
        organization: org || undefined,
        date: date || undefined,
      });
      continue;
    }

    // If it's a bullet or paragraph, parse as a certification entry if possible
    if (block.type === "bullet" || block.type === "paragraph") {
      const text = (block.text || "")
        .replace(/^[\u2022\u25CF\u25AA\u25AB\u25BA\u2043\u2013\u2014\-*]\s*/, "")
        .trim();
      if (!text) {
        result.push(block);
        continue;
      }

      let org: string | undefined;
      let title = text;
      let date: string | undefined;

      const dMatch = text.match(EXTRACT_DATE_REGEX);
      if (dMatch && (text.endsWith(`(${dMatch[0]})`) || text.endsWith(dMatch[0]))) {
        date = dMatch[0];
        title = text
          .replace(`(${dMatch[0]})`, "")
          .replace(dMatch[0], "")
          .trim()
          .replace(/[-–—|]$/, "")
          .trim();
      }

      if (title.includes("|")) {
        const parts = title.split("|").map((p) => p.trim()).filter(Boolean);
        if (parts.length > 1) {
          const p0Lower = parts[0].toLowerCase();
          if (CERT_KNOWN_ISSUERS.some((ki) => p0Lower.includes(ki))) {
            org = parts[0];
            title = parts.slice(1).join(" | ");
          } else {
            title = parts[0];
            org = parts.slice(1).join(" | ");
          }
        }
      } else if (/\s+[—–-]\s+/.test(title)) {
        const parts = title.split(/\s+[—–-]\s+/).map((p) => p.trim()).filter(Boolean);
        if (parts.length > 1) {
          const p0Lower = parts[0].toLowerCase();
          if (CERT_KNOWN_ISSUERS.some((ki) => p0Lower.includes(ki))) {
            org = parts[0];
            title = parts.slice(1).join(" - ");
          } else {
            title = parts[0];
            org = parts.slice(1).join(" - ");
          }
        }
      }

      result.push({
        ...block,
        type: "entry",
        title,
        organization: org,
        date,
        bullets: [],
      } as unknown as CVBlock);
      continue;
    }

    result.push(block);
  }

  return result;
}

/** Deep-clone a CVDocumentV2 so per-section edits never mutate the draft in place. */
export function cloneDocument(doc: CVDocumentV2 | null): CVDocumentV2 {
  if (!doc) {
    return {
      raw_extraction_id: null,
      schema_version: 2,
      extraction_version: "2.0",
      parser_version: "deterministic-prefill-1.0",
      reconstruction_version: CURRENT_RECONSTRUCTION_VERSION,
      requires_reprocessing: false,
      source_hash: null,
      identity: { full_name: null, headline: null, email: null, phone: null, location: null, links: [], source_block_ids: [], field_source_block_ids: { full_name: [], headline: [], email: [], phone: [], location: [], links: {} }, hidden_fields: [], name: "", contact_lines: [] },
      summary: null,
      sections: [],
      unmapped_content: [],
      reconstruction_warnings: [],
    };
  }
  return {
    ...doc,
    identity: { ...doc.identity, field_source_block_ids: { ...doc.identity.field_source_block_ids } },
    summary: doc.summary ? cloneBlock(doc.summary) as CVParagraphBlock : null,
    sections: doc.sections
      .filter((section) => !isSuppressedCustomSection(section))
      .map((section) => {
        const clonedBlocks = section.blocks.map(cloneBlock);
        const isSkill = section.type === "skills" || /skill/i.test(section.title ?? "");
        const isCert = section.type === "certifications" || /certif/i.test(section.title ?? "");
        let blocks = clonedBlocks;
        if (isSkill) {
          blocks = normalizeSkillsBlocks(blocks);
        } else if (isCert) {
          blocks = normalizeCertificationsBlocks(blocks);
        }
        return {
          ...section,
          source_block_ids: [...section.source_block_ids],
          blocks,
        };
      }),
    unmapped_content: doc.unmapped_content.map((item) => ({ ...item })),
    reconstruction_warnings: [...doc.reconstruction_warnings],
    reconstruction_diagnostics: doc.reconstruction_diagnostics
      ? { ...doc.reconstruction_diagnostics }
      : undefined,
  };
}

function cloneBlock(block: CVBlock): CVBlock {
  const base: CVBlockMetadata = {
    ...(block as CVBlockMetadata),
    source_block_ids: block.source_block_ids ? [...block.source_block_ids] : undefined,
    source_line_ids: (block as CVBlockMetadata).source_line_ids
      ? [...(block as CVBlockMetadata).source_line_ids!]
      : undefined,
  };
  switch (block.type) {
    case "entry":
      return { ...base, bullets: [...block.bullets] } as CVEntryBlock;
    case "skill_group":
      return { ...base, skills: [...block.skills] } as CVBlock;
    case "publication":
      return { ...base } as CVBlock;
    case "education":
      return { ...base, details: [...block.details] } as CVBlock;
    case "unknown":
      return { ...base, lines: [...block.lines] } as CVBlock;
    default:
      return { ...base } as CVBlock;
  }
}

/**
 * Merge a form patch into one block and mark that block as user-edited.
 * Only the touched block gets origin=user_edit; untouched siblings keep
 * their provenance. The cast is safe: callers pass a patch of the block's
 * own member type (Partial<CVEntryBlock>, ...).
 */
export function applyBlockPatch(block: CVBlock, patch: Partial<CVBlock>): CVBlock {
  return { ...block, ...patch, origin: "user_edit" } as CVBlock;
}

/** Build the canonical contact lines the identity form binds to. */
export function identityContactFields(identity: CVIdentity): {
  full_name: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
  links: string[];
} {
  return {
    full_name: identity.full_name ?? "",
    headline: identity.headline ?? "",
    email: identity.email ?? "",
    phone: identity.phone ?? "",
    location: identity.location ?? "",
    links: identity.links ? [...identity.links] : [],
  };
}

/** The set of identity field keys the privacy toggle can hide. */
export const IDENTITY_HIDDEN_FIELD_KEYS: Array<keyof CVIdentity> = [
  "full_name",
  "headline",
  "email",
  "phone",
  "location",
  "links",
];

/** A stable empty block_id for freshly added entries. */
export function freshBlockId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

/** A skipped-empty summary must not export: drop it before save/mint. */
export function dropEmptySummary(doc: CVDocumentV2): CVDocumentV2 {
  if (doc.summary && !doc.summary.text.trim()) {
    return { ...doc, summary: null };
  }
  return doc;
}