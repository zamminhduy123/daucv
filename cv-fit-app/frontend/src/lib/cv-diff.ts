"use client";

import type { CVBlock, CVDocumentV2 } from "@/types";

export interface WordToken {
  text: string;
  kind: "same" | "del" | "add";
}

export interface BlockDiff {
  id: string;
  sectionTitle: string;
  label: string;
  before: string;
  after: string;
  beforeWords: WordToken[];
  afterWords: WordToken[];
}

function blockText(block: CVBlock): string | null {
  if (block.type === "paragraph" || block.type === "bullet") {
    return (block as { text?: string }).text ?? null;
  }
  return null;
}

function blockBullets(block: CVBlock): string[] | null {
  if (block.type === "entry") {
    const bullets = (block as { bullets?: string[] }).bullets;
    return Array.isArray(bullets) ? bullets : null;
  }
  if (block.type === "education") {
    const details = (block as { details?: string[] }).details;
    return Array.isArray(details) ? details : null;
  }
  return null;
}

function blockLabel(block: CVBlock): string {
  if (block.type === "entry") {
    const entry = block as { title?: string | null; organization?: string | null };
    return entry.title || entry.organization || block.block_id;
  }
  if (block.type === "education") {
    const edu = block as { institution?: string | null; degree?: string | null };
    return edu.institution || edu.degree || block.block_id;
  }
  if (block.type === "skill_group") {
    return (block as { label?: string | null }).label || block.block_id;
  }
  if (block.type === "publication") {
    return (block as { title?: string | null }).title || block.block_id;
  }
  return block.block_id;
}

/** LCS-based word diff. Returns per-side token lists with same/del/add marks. */
export function wordDiff(before: string, after: string): { beforeWords: WordToken[]; afterWords: WordToken[] } {
  const a = before.split(/(\s+)/).filter((t) => t.length > 0);
  const b = after.split(/(\s+)/).filter((t) => t.length > 0);
  const n = a.length;
  const m = b.length;
  // Cap quadratic DP for very long bullets (320 chars max from backend anyway).
  if (n * m > 40_000) {
    if (before === after) {
      return {
        beforeWords: a.map((text) => ({ text, kind: "same" as const })),
        afterWords: b.map((text) => ({ text, kind: "same" as const })),
      };
    }
    return {
      beforeWords: a.map((text) => ({ text, kind: "del" as const })),
      afterWords: b.map((text) => ({ text, kind: "add" as const })),
    };
  }
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const beforeWords: WordToken[] = [];
  const afterWords: WordToken[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      beforeWords.push({ text: a[i], kind: "same" });
      afterWords.push({ text: b[j], kind: "same" });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      beforeWords.push({ text: a[i], kind: "del" });
      i++;
    } else {
      afterWords.push({ text: b[j], kind: "add" });
      j++;
    }
  }
  while (i < n) beforeWords.push({ text: a[i++], kind: "del" });
  while (j < m) afterWords.push({ text: b[j++], kind: "add" });
  return { beforeWords, afterWords };
}

/**
 * Compare two structured CV documents block-by-block (matched by block_id).
 * Only Grounded Rewrite text changes surface: paragraph text + entry bullets.
 * Identity/summary-hidden flags and ordering are intentionally ignored.
 */
export function diffDocuments(before: CVDocumentV2 | null | undefined, after: CVDocumentV2 | null | undefined): BlockDiff[] {
  if (!before || !after) return [];
  const diffs: BlockDiff[] = [];

  // Summary paragraph.
  const beforeSummary = before.summary?.hidden ? null : before.summary?.text?.trim();
  const afterSummary = after.summary?.hidden ? null : after.summary?.text?.trim();
  if (beforeSummary !== afterSummary && (beforeSummary || afterSummary)) {
    const { beforeWords, afterWords } = wordDiff(beforeSummary ?? "", afterSummary ?? "");
    diffs.push({
      id: "summary",
      sectionTitle: "Tóm tắt",
      label: "Tóm tắt",
      before: beforeSummary ?? "",
      after: afterSummary ?? "",
      beforeWords,
      afterWords,
    });
  }

  const beforeSections = new Map(before.sections.map((s) => [s.id, s]));
  for (const section of after.sections) {
    const prev = beforeSections.get(section.id);
    if (!prev) continue;
    const prevBlocks = new Map(prev.blocks.map((b) => [b.block_id, b]));
    for (const block of section.blocks) {
      if (block.hidden) continue;
      const old = prevBlocks.get(block.block_id);
      if (!old || old.hidden) continue;
      const label = blockLabel(block);

      const newText = blockText(block);
      const oldText = blockText(old);
      if (newText !== null || oldText !== null) {
        if ((oldText ?? "") !== (newText ?? "")) {
          const { beforeWords, afterWords } = wordDiff(oldText ?? "", newText ?? "");
          diffs.push({
            id: `${section.id}:${block.block_id}:text`,
            sectionTitle: section.title || section.type,
            label,
            before: oldText ?? "",
            after: newText ?? "",
            beforeWords,
            afterWords,
          });
        }
        continue;
      }

      const newBullets = blockBullets(block);
      const oldBullets = blockBullets(old);
      if (newBullets && oldBullets) {
        const len = Math.max(oldBullets.length, newBullets.length);
        for (let k = 0; k < len; k++) {
          const o = (oldBullets[k] ?? "").trim();
          const v = (newBullets[k] ?? "").trim();
          if (o !== v && (o || v)) {
            const { beforeWords, afterWords } = wordDiff(oldBullets[k] ?? "", newBullets[k] ?? "");
            diffs.push({
              id: `${section.id}:${block.block_id}:bullets[${k}]`,
              sectionTitle: section.title || section.type,
              label: `${label} · gạch đầu dòng ${k + 1}`,
              before: oldBullets[k] ?? "",
              after: newBullets[k] ?? "",
              beforeWords,
              afterWords,
            });
          }
        }
      }
    }
  }
  return diffs;
}
