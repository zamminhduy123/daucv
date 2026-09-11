"""Experimental LLM #1 v3.1: cursor plan -> exact server-side rendering.

This service is offline-only. Production remains on the semantic V1 mapper
until shadow comparison proves V3 meets fidelity and compatibility gates.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError

from app.core.config import (
    CV_RANGE_PLAN_SECTION_MAX_OUTPUT_TOKENS,
    CV_STRUCTURING_MAX_RETRIES,
    LOGS_DIR,
)
from app.models.cv_document_v2 import (
    _JOB_TITLE_KEYWORDS,
    CVBulletBlock,
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVIdentity,
    CVIdentitySourceMap,
    CVParagraphBlock,
    CVPublicationBlock,
    CVSection,
    CVSkillGroupBlock,
    CVUnknownBlock,
    unwrap_google_redirect_url,
)
from app.models.cv_range_plan import (
    LLMSectionCursorPlanResponse,
    LLMVisualEntryHeaderResponse,
    SourceLedgerAtom,
)
from app.models.cv_raw_extraction import RawBlock, RawExtraction
from app.prompts.system_prompts import (
    build_section_range_plan_prompt,
    build_visual_entry_header_prompt,
    format_source_ledger,
    format_visual_entry_header,
)
from app.services.ai_service import call_llm_with_fallback
from app.services.cv_reconstruction_service import (
    canonical_cv_hash,
    finalize_document_provenance,
)
from app.services.cv_source_grounding import normalize_grounding_text
from app.services.cv_structuring_service import (
    ParserRetryReporter,
    deterministic_structuring_fallback,
    resolve_authoritative_source,
)
from app.services.files import FileService
from app.services.layout_extraction import (
    join_logical_blocks,
    raw_extraction_to_text,
    read_blocks_in_order,
    validate_raw_extraction,
)
from app.services.section_vocabulary import classify_heading


class InvalidRangePlanError(ValueError):
    """A cursor plan cannot be compiled against the local source ledger."""


_FRAGMENT_RE = re.compile(r"[^\n|•·]+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
_LINK_RE = re.compile(
    r"(?:https?://|www\.)[^\s|•,;]+|(?:linkedin|github)\.com/[^\s|•,;]+|"
    r"^(?:linkedin|github|website|portfolio|google scholar|scholar|kaggle|blog)$",
    re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    r"^(?:[A-Za-zÀ-ỹ][A-Za-zÀ-ỹ .'-]+,\s*[A-Za-zÀ-ỹ .'-]+|Remote|Hybrid|On-site)$",
    re.IGNORECASE,
)
_GEOGRAPHIC_TOKEN_RE = re.compile(
    r"\b(?:city|district|province|state|vietnam|korea|japan|singapore|"
    r"usa|united states|canada|australia|remote|hybrid|on-site)\b",
    re.IGNORECASE,
)

_SECTION_KINDS: dict[str, set[str]] = {
    "education": {"d", "x"},
    "skills": {"s", "x", "u"},
    "publications": {"u", "x"},
    "certifications": {"e", "x"},
    "experience": {"e", "b", "x"},
    "projects": {"e", "b", "x"},
}
_ROLES_BY_KIND: dict[str, set[str]] = {
    "e": {"t", "s", "o", "l", "d", "b"},
    "b": {"x"},
    "p": {"x"},
    "s": {"g", "k"},
    "u": {"t", "a", "v", "d", "q", "u"},
    "d": {"i", "t", "m", "l", "d", "n"},
    "x": {"u"},
}
_REPEATABLE_ROLES = {"b", "k", "n", "u"}
_ENTRY_ANCHOR_BY_KIND = {"e": "t", "d": "i", "u": "t", "s": "g"}
_BULLET_PREFIX_RE = re.compile(r"^(?:[-–—•▪‣])\s*")
_NAME_STOP_WORDS = frozenset(
    {
        "the",
        "of",
        "and",
        "in",
        "for",
        "with",
        "to",
        "from",
        "developer",
        "engineer",
        "scientist",
        "professional",
        "skills",
        "experience",
        "projects",
        "education",
        "activities",
        "awards",
        "interests",
        "publications",
        "summary",
        "profile",
        "contact",
        "certifications",
        "kỹ",
        "nghệ",
        "sư",
        "nghiem",
        "nghiệm",
        "học",
        "tóm",
        "tắt",
        "giới",
        "thiệu",
        "mục",
        "tiêu",
        "sơ",
        "lược",
        "hoạt",
        "động",
    }
)
_MAX_NAME_WORDS = 4


def _looks_like_name(text: str) -> bool:
    """Conservative classifier: returns True when a preamble atom looks like a
    person's name. Mirrors the V1 ``_looks_like_name`` heuristic so V3 can
    recover names that sit at non-zero offsets in a mixed preamble (e.g. when
    email is sorted above the name line)."""
    stripped = text.strip()
    if not stripped:
        return False
    if (
        "@" in stripped
        or _EMAIL_RE.search(stripped)
        or _LINK_RE.search(stripped)
        or _PHONE_RE.search(stripped)
    ):
        return False
    if "|" in stripped or _JOB_TITLE_KEYWORDS.search(stripped):
        return False
    if re.search(r"[@<>{}[\]\\/~_+=^%$#*0-9]", stripped):
        return False
    words = stripped.split()
    if len(words) > _MAX_NAME_WORDS or len(words) < 1:
        return False
    if not any(len(word) >= 2 for word in words):
        return False
    if any(word.lower() in _NAME_STOP_WORDS for word in words if len(word) > 2):
        return False
    cased_words = sum(1 for w in words if w.istitle() or w.isupper())
    if len(words) == 1:
        return cased_words == 1 and len(words[0]) >= 3
    return cased_words >= len(words) - 1


@dataclass(frozen=True)
class _LedgerSection:
    type: str
    title: SourceLedgerAtom
    content: list[SourceLedgerAtom]


@dataclass(frozen=True)
class _ResolvedBlock:
    kind: str
    fields: list[tuple[str, list[SourceLedgerAtom]]]


@dataclass(frozen=True)
class CVRangePlanResult:
    raw_extraction: RawExtraction
    source_text: str
    document: CVDocumentV2
    ledger_atom_count: int
    unclassified_atom_indexes: list[int]
    used_fallback: bool
    section_failures: list[str]


def build_source_ledger(raw: RawExtraction) -> list[SourceLedgerAtom]:
    """Build server-owned offset atoms; no durable IDs are sent to the model.

    Atoms before the first section heading (the identity preamble) keep
    the PDF's original reading order so contact atoms stay interleaved
    with the name atom regardless of column placement.  Atoms within
    sections are emitted in column-major reading order via
    ``read_blocks_in_order`` so two-column layouts reach the cursor
    planner correctly.

    The split is determined by ``classify_heading``: every block whose
    text is a known section heading marks the start of a new section,
    and every block before the first heading belongs to the preamble.

    Section blocks are first merged via ``join_logical_blocks`` so one
    visual bullet/citation (possibly wrapped across physical PDF lines)
    becomes one ledger atom. The preamble is never joined: identity
    lines must stay separate atoms.
    """
    validate_raw_extraction(raw)
    ordered_blocks = read_blocks_in_order(raw)

    heading_block_ids: set[str] = {
        block.block_id
        for page in raw.pages
        for block in page.blocks
        if classify_heading(block.text) is not None
    }

    original_blocks: list[RawBlock] = []
    for page in raw.pages:
        original_blocks.extend(page.blocks)
    original_index: dict[str, int] = {
        block.block_id: index for index, block in enumerate(original_blocks)
    }

    first_heading_id: str | None = next(
        (
            original_blocks[index].block_id
            for index in sorted(
                {
                    original_index[block_id]
                    for block_id in heading_block_ids
                    if block_id in original_index
                }
            )
        ),
        None,
    )
    if first_heading_id is not None:
        first_heading_original_index = original_index[first_heading_id]
        preamble_ids = {
            block.block_id for block in original_blocks[:first_heading_original_index]
        }
    else:
        preamble_ids = {block.block_id for block in original_blocks}

    ordered_for_ledger: list[RawBlock] = []
    seen_ids: set[str] = set()
    for block in ordered_blocks:
        if block.block_id in preamble_ids and block.block_id not in seen_ids:
            ordered_for_ledger.append(block)
            seen_ids.add(block.block_id)
    for block in ordered_blocks:
        if block.block_id not in seen_ids:
            ordered_for_ledger.append(block)
            seen_ids.add(block.block_id)

    page_sizes: dict[int, tuple[float | None, float | None]] = {
        page.page: (page.width, page.height) for page in raw.pages
    }
    preamble_blocks = [
        block for block in ordered_for_ledger if block.block_id in preamble_ids
    ]
    section_blocks = [
        block for block in ordered_for_ledger if block.block_id not in preamble_ids
    ]
    joined_sections = join_logical_blocks(
        section_blocks,
        heading_block_ids=heading_block_ids,
        page_sizes=page_sizes,
    )

    ledger: list[SourceLedgerAtom] = []
    for block in preamble_blocks:
        for match in _FRAGMENT_RE.finditer(block.text):
            fragment = match.group(0)
            start = match.start() + len(fragment) - len(fragment.lstrip())
            end = match.end() - len(fragment) + len(fragment.rstrip())
            text = normalize_grounding_text(block.text[start:end])
            if text:
                ledger.append(
                    SourceLedgerAtom(
                        index=len(ledger),
                        block_id=block.block_id,
                        text=text,
                        page=block.page,
                        reading_order=len(ledger),
                        bbox=block.bbox,
                        is_bullet=bool(_BULLET_PREFIX_RE.match(block.text)),
                        start_offset=start,
                        end_offset=end,
                        source_block_ids=[block.block_id],
                    )
                )
    for block, constituent_ids in joined_sections:
        for match in _FRAGMENT_RE.finditer(block.text):
            fragment = match.group(0)
            start = match.start() + len(fragment) - len(fragment.lstrip())
            end = match.end() - len(fragment) + len(fragment.rstrip())
            text = normalize_grounding_text(block.text[start:end])
            if text:
                ledger.append(
                    SourceLedgerAtom(
                        index=len(ledger),
                        block_id=block.block_id,
                        text=text,
                        page=block.page,
                        reading_order=len(ledger),
                        bbox=block.bbox,
                        is_bullet=bool(_BULLET_PREFIX_RE.match(block.text)),
                        start_offset=start,
                        end_offset=end,
                        source_block_ids=list(constituent_ids),
                    )
                )
    if not ledger:
        raise InvalidRangePlanError("Raw extraction contains no usable source atoms")
    return ledger


def _partition_ledger(
    ledger: list[SourceLedgerAtom],
) -> tuple[list[SourceLedgerAtom], list[_LedgerSection]]:
    headings = [
        (index, match[0])
        for index, atom in enumerate(ledger)
        if (match := classify_heading(atom.text)) is not None
    ]
    if not headings:
        raise InvalidRangePlanError("No deterministic CV section headings found")
    sections = [
        _LedgerSection(
            section_type,
            ledger[start],
            ledger[
                start + 1 : headings[index + 1][0]
                if index + 1 < len(headings)
                else len(ledger)
            ],
        )
        for index, (start, section_type) in enumerate(headings)
    ]
    return ledger[: headings[0][0]], sections


def _join(atoms: list[SourceLedgerAtom]) -> str | None:
    return " ".join(atom.text for atom in atoms) if atoms else None


def _block_ids(atoms: list[SourceLedgerAtom]) -> list[str]:
    ids: list[str] = []
    for atom in atoms:
        constituents = atom.source_block_ids or [atom.block_id]
        for block_id in constituents:
            if block_id not in ids:
                ids.append(block_id)
    return ids


def _build_identity(preamble: list[SourceLedgerAtom]) -> tuple[CVIdentity, set[int]]:
    assigned: set[int] = set()
    values: dict[str, SourceLedgerAtom | None] = {
        key: None for key in ("name", "email", "phone", "location")
    }
    headline_atoms: list[SourceLedgerAtom] = []
    name_atoms: list[SourceLedgerAtom] = []
    prev_was_name = False
    links: list[str] = []
    link_sources: dict[str, list[str]] = {}
    for atom in preamble:
        text = atom.text.strip()
        if not text:
            continue
        if _EMAIL_RE.search(text) and values["email"] is None:
            values["email"] = atom
            prev_was_name = False
        elif _PHONE_RE.search(text) and values["phone"] is None:
            values["phone"] = atom
            prev_was_name = False
        elif match := _LINK_RE.search(text):
            link = unwrap_google_redirect_url(match.group(0).rstrip(".)]"))
            links.append(link)
            link_sources[link] = [atom.block_id]
            prev_was_name = False
        elif _LOCATION_RE.fullmatch(text) and values["location"] is None:
            values["location"] = atom
            prev_was_name = False
        elif values["name"] is None and _looks_like_name(text):
            values["name"] = atom
            name_atoms = [atom]
            prev_was_name = True
        elif (
            prev_was_name
            and not headline_atoms
            and _looks_like_name(text)
            and _looks_like_name(f"{name_atoms[0].text} {text}")
        ):
            # Multi-line candidate name (first/last name on separate PDF
            # lines). The combined text must still read as one name so a
            # headline on the next line never merges in.
            name_atoms.append(atom)
            prev_was_name = True
        elif (
            values["name"] is not None
            and not _EMAIL_RE.search(text)
            and not _PHONE_RE.search(text)
            and not _LINK_RE.search(text)
            and not (_LOCATION_RE.fullmatch(text) and _GEOGRAPHIC_TOKEN_RE.search(text))
        ):
            headline_atoms.append(atom)
            prev_was_name = False
        else:
            prev_was_name = False
            continue
        assigned.add(atom.index)

    if values["name"] and (
        _EMAIL_RE.search(values["name"].text) or "@" in values["name"].text
    ):
        email_atom = values["name"]
        candidate_name_atom = None
        for h_atom in headline_atoms:
            if _looks_like_name(h_atom.text):
                candidate_name_atom = h_atom
                break
        if candidate_name_atom:
            headline_atoms.remove(candidate_name_atom)
            values["name"] = candidate_name_atom
            name_atoms = [candidate_name_atom]
        else:
            values["name"] = None
            name_atoms = []
        if values["email"] is None:
            values["email"] = email_atom

    if len(name_atoms) > 1:
        combined = " ".join(atom.text.strip() for atom in name_atoms)
        first = name_atoms[0]
        values["name"] = first.model_copy(
            update={
                "text": combined,
                "end_offset": first.start_offset + len(combined),
                "source_block_ids": _block_ids(name_atoms),
            }
        )

    def value(key: str, pattern: re.Pattern[str] | None = None) -> str | None:
        atom = values[key]
        if atom is None:
            return None
        match = pattern.search(atom.text) if pattern else None
        return match.group(0).rstrip(".)]") if match else atom.text

    def source(key: str) -> list[str]:
        atom = values[key]
        if atom is None:
            return []
        return list(dict.fromkeys(atom.source_block_ids or [atom.block_id]))

    headline_text = (
        " / ".join(atom.text for atom in headline_atoms) if headline_atoms else None
    )
    headline_sources = list(dict.fromkeys(atom.block_id for atom in headline_atoms))

    assigned_block_ids = list(
        dict.fromkeys(atom.block_id for atom in preamble if atom.index in assigned)
    )
    return CVIdentity(
        full_name=value("name"),
        headline=headline_text,
        email=value("email", _EMAIL_RE),
        phone=value("phone", _PHONE_RE),
        location=value("location"),
        links=list(dict.fromkeys(links)),
        source_block_ids=assigned_block_ids,
        field_source_block_ids=CVIdentitySourceMap(
            full_name=source("name"),
            headline=headline_sources,
            email=source("email"),
            phone=source("phone"),
            location=source("location"),
            links=link_sources,
        ),
    ), assigned


def _split_repeated_anchor(block: _ResolvedBlock) -> list[_ResolvedBlock]:
    """Split repeated record anchors without moving any source ownership."""
    anchor = _ENTRY_ANCHOR_BY_KIND.get(block.kind)
    if not anchor:
        return [block]
    chunks: list[list[tuple[str, list[SourceLedgerAtom]]]] = [[]]
    for role, atoms in block.fields:
        if role == anchor and any(
            existing_role == anchor for existing_role, _ in chunks[-1]
        ):
            chunks.append([])
        chunks[-1].append((role, atoms))
    return [_ResolvedBlock(block.kind, fields) for fields in chunks if fields]


def compile_section_cursor_plan(
    section: _LedgerSection, plan: LLMSectionCursorPlanResponse
) -> tuple[list[_ResolvedBlock], bool]:
    """Consume the local ledger exactly once; cursor design prevents overlap.

    Returns ``(blocks, count_mismatch_clamped)``. When the planner's counts
    do not total exactly ``len(section.content)``, counts are clamped to
    preserve every atom (partial content beats total loss) and the flag is
    set so the caller can record a loud ``cursor_plan_count_mismatch_clamped``
    reconstruction warning instead of failing silently. Only structural
    violations (forbidden kind/role, repeated scalar role) raise.
    """
    cursor = 0
    compiled: list[_ResolvedBlock] = []
    clamped = False
    permitted_kinds = _SECTION_KINDS.get(section.type)
    for block_index, block in enumerate(plan.blocks):
        if permitted_kinds is not None and block.kind not in permitted_kinds:
            raise InvalidRangePlanError(
                f"forbidden kind {block.kind!r} for {section.type}"
            )
        allowed_roles = _ROLES_BY_KIND[block.kind]
        fields: list[tuple[str, list[SourceLedgerAtom]]] = []
        for segment_index, segment in enumerate(block.segments):
            if segment.role not in allowed_roles:
                raise InvalidRangePlanError(
                    f"forbidden role {segment.role!r} for kind {block.kind}"
                )

            # The ledger holds logical atoms (wraps joined upstream). When the
            # planner's counts overshoot the section end, clamp to preserve
            # every atom (partial content beats total section loss) and flag
            # the mismatch so the caller records a loud warning instead of
            # failing silently or dropping planned roles.
            if cursor >= len(section.content):
                _logger.warning(
                    "Cursor plan overrun clamped at segment %d:%d "
                    "(section %s has %d atoms)",
                    block_index,
                    segment_index,
                    section.type,
                    len(section.content),
                )
                clamped = True
                break

            count = segment.count
            # For repeatable list roles, clamp count so it never over-consumes
            # past the end of section.
            if segment.role in _REPEATABLE_ROLES:
                clamped_count = min(count, len(section.content) - cursor)
                if clamped_count != count:
                    clamped = True
                count = clamped_count
                # If this is the final segment of the final block, absorb all remaining section atoms
                is_final_segment = (
                    block_index == len(plan.blocks) - 1
                    and segment_index == len(block.segments) - 1
                )
                if is_final_segment:
                    count = len(section.content) - cursor

            end = cursor + count
            if end > len(section.content):
                _logger.warning(
                    "Cursor plan scalar overrun clamped at segment %d:%d "
                    "(section %s has %d atoms)",
                    block_index,
                    segment_index,
                    section.type,
                    len(section.content),
                )
                clamped = True
                end = len(section.content)

            if end > cursor:
                fields.append((segment.role, section.content[cursor:end]))
                cursor = end

        if fields:
            compiled.extend(_split_repeated_anchor(_ResolvedBlock(block.kind, fields)))

    # If all blocks finished but some trailing atoms remain, absorb them into the last block
    if cursor < len(section.content) and compiled:
        clamped = True
        remaining_atoms = section.content[cursor:]
        last_block = compiled[-1]
        last_role = last_block.fields[-1][0] if last_block.fields else None
        if last_role in _REPEATABLE_ROLES:
            *other_fields, (role, atoms) = last_block.fields
            compiled[-1] = _ResolvedBlock(
                last_block.kind,
                [*other_fields, (role, [*atoms, *remaining_atoms])],
            )
            cursor = len(section.content)
        else:
            fallback_role = (
                "b"
                if last_block.kind in {"e", "b"}
                else ("n" if last_block.kind == "d" else "u")
            )
            compiled[-1] = _ResolvedBlock(
                last_block.kind,
                [*last_block.fields, (fallback_role, remaining_atoms)],
            )
            cursor = len(section.content)

    if cursor != len(section.content):
        raise InvalidRangePlanError(
            f"cursor consumed {cursor}/{len(section.content)} source atoms"
        )
    for block in compiled:
        seen: set[str] = set()
        if any(
            role in seen or seen.add(role)
            for role, _ in block.fields
            if role not in _REPEATABLE_ROLES
        ):
            raise InvalidRangePlanError(
                f"repeated scalar role remains in kind {block.kind}"
            )
    return compiled, clamped


def _render_block(block: _ResolvedBlock, *, block_id: str):
    fields: dict[str, list[list[SourceLedgerAtom]]] = {}
    for role, atoms in block.fields:
        fields.setdefault(role, []).append(atoms)

    def single(role: str) -> str | None:
        groups = fields.get(role, [])
        return _join(groups[0]) if groups else None

    def multiple(role: str) -> list[str]:
        # Each source atom is already one logical visual line group:
        # physical PDF wraps are joined upstream in build_source_ledger
        # via join_logical_blocks, so one atom equals one bullet/detail.
        _per_atom_roles = {"b", "n", "k"}
        groups = fields.get(role, [])
        if role in _per_atom_roles:
            items: list[str] = []
            for group in groups:
                for atom in group:
                    text = atom.text.strip()
                    if text:
                        items.append(text)
            return items
        return [_join(group) or "" for group in groups]

    source_atoms = [
        atom for groups in fields.values() for group in groups for atom in group
    ]
    common = {"block_id": block_id, "source_block_ids": _block_ids(source_atoms)}
    if block.kind == "e":
        return CVEntryBlock(
            **common,
            title=single("t") or "",
            subtitle=single("s"),
            organization=single("o"),
            location=single("l"),
            date=single("d"),
            bullets=multiple("b"),
        )
    if block.kind == "b":
        return CVBulletBlock(**common, text=single("x") or "")
    if block.kind == "p":
        return CVParagraphBlock(**common, text=single("x") or "")
    if block.kind == "s":
        raw_label = single("g")
        raw_skills = multiple("k")
        # Handle case where the LLM put 'Category: item1, item2' all in the label atom
        if raw_label and ":" in raw_label:
            cat, rest = raw_label.split(":", 1)
            raw_label = cat.strip()
            # Extract skills from the label's "Category: item1, item2" format
            label_rest_skills = [s.strip() for s in rest.split(",") if s.strip()]
            # Append k-role items after (they may be other category lines;
            # _normalize_skill_groups will expand those into separate blocks)
            raw_skills = label_rest_skills + [s for s in raw_skills if s.strip()]
        return CVSkillGroupBlock(**common, label=raw_label, skills=raw_skills)
    if block.kind == "u":
        return CVPublicationBlock(
            **common,
            title=single("t") or "",
            authors=single("a"),
            venue=single("v"),
            date=single("d"),
            status=single("q"),
        )
    if block.kind == "d":
        return CVEducationBlock(
            **common,
            institution=single("i"),
            degree=single("t"),
            field=single("m"),
            location=single("l"),
            date=single("d"),
            details=multiple("n"),
        )
    return CVUnknownBlock(**common, lines=multiple("u"), confidence=0.0)


def _normalize_skill_groups(blocks: list, section_type: str) -> list:
    """Post-process skill_group blocks to ensure each category line is its own block.

    The LLM sometimes treats two consecutive skill category lines as:
      block 1: label='Category A', skills=['Category B: item1, item2']
    instead of two separate blocks. This function detects and expands that pattern.
    """
    if section_type != "skills":
        return blocks
    result = []
    for block in blocks:
        if not isinstance(block, CVSkillGroupBlock):
            result.append(block)
            continue
        # Check if any skill item looks like 'Category: items' — a misclassified category line
        extra_blocks: list[CVSkillGroupBlock] = []
        clean_skills: list[str] = []
        for skill_item in block.skills:
            if ":" in skill_item:
                # Check it's not just a normal skill name with a colon (version numbers etc.)
                cat_part, rest_part = skill_item.split(":", 1)
                # A category label: title-like text (letters/spaces/&), rest has actual skills
                if (
                    len(cat_part.strip()) > 2
                    and re.match(r"^[A-Za-z\s&./+-]{2,40}$", cat_part.strip())
                    and rest_part.strip()
                ):
                    # This is a new category
                    extra_blocks.append(
                        CVSkillGroupBlock(
                            block_id=f"{block.block_id}-extra-{len(extra_blocks)}",
                            source_block_ids=block.source_block_ids,
                            label=cat_part.strip(),
                            skills=[
                                s.strip() for s in rest_part.split(",") if s.strip()
                            ],
                        )
                    )
                    continue
            clean_skills.append(skill_item)
        if extra_blocks:
            # Replace block with its cleaned version (no category-looking skills)
            cleaned = CVSkillGroupBlock(
                block_id=block.block_id,
                source_block_ids=block.source_block_ids,
                label=block.label,
                skills=clean_skills,
            )
            result.append(cleaned)
            result.extend(extra_blocks)
        else:
            result.append(block)
    return result


def _unknown_section_block(section: _LedgerSection) -> CVUnknownBlock:
    return CVUnknownBlock(
        block_id=f"range-plan-{section.title.index}-unknown",
        lines=[atom.text for atom in section.content],
        source_block_ids=_block_ids(section.content),
    )


def _visual_entry_header_positions(section: _LedgerSection) -> set[int]:
    """Find a geometry-backed header before the first visible entry bullet.

    PDF reading order often yields company/location then role/date on two
    adjacent visual rows.  Those four fragments are one entry header, not four
    unrelated sequential fields.  This returns only an annotation for the
    planner; text ownership and rendering remain server-owned.

    Because ``build_source_ledger`` now feeds column-major reading order,
    the header atoms may be split across stream positions (left column
    items first, then right column items, with a bullet in between).  We
    therefore group atoms by Y-band (top-down) and within each band by X
    (left-to-right), and return the indices of every atom in the header
    band(s) that appear before the first bullet's Y.
    """
    if section.type not in {"experience", "projects"}:
        return set()
    atoms_with_bbox = [
        (index, atom)
        for index, atom in enumerate(section.content)
        if atom.bbox is not None
    ]
    if len(atoms_with_bbox) < 2:
        return set()

    bullet_y = next(
        (
            atom.bbox[1]
            for atom in section.content
            if atom.is_bullet or _BULLET_PREFIX_RE.match(atom.text)
        ),
        None,
    )

    prefix = [
        (index, atom)
        for index, atom in atoms_with_bbox
        if bullet_y is None or atom.bbox[1] < bullet_y
    ]
    if len(prefix) < 2:
        return set()
    y_values = [atom.bbox[1] for _, atom in prefix]
    if max(y_values) - min(y_values) > 36.0:
        return set()
    return {index for index, _ in prefix}


async def _plan_visual_entry_header(
    section: _LedgerSection,
    positions: set[int],
    *,
    background_tasks: BackgroundTasks | None,
    on_retry: ParserRetryReporter | None,
) -> dict[int, str] | None:
    """Classify one small visual header independently from section planning.

    Header atoms are sorted by visual position (top-to-bottom, left-to-right)
    before being passed to the model so the response roles map back to the
    correct stream positions regardless of how ``build_source_ledger`` has
    ordered atoms.
    """
    header_atoms = [
        (position, section.content[position])
        for position in positions
        if section.content[position].bbox is not None
    ]
    header_atoms.sort(
        key=lambda pair: (
            pair[1].bbox[1] if pair[1].bbox else 0.0,
            pair[1].bbox[0] if pair[1].bbox else 0.0,
        )
    )
    ordered_positions = [position for position, _ in header_atoms]
    atoms = [atom for _, atom in header_atoms]
    if not 2 <= len(atoms) <= 6:
        return None
    value = await call_llm_with_fallback(
        build_visual_entry_header_prompt(section.title.text),
        format_visual_entry_header(atoms),
        LLMVisualEntryHeaderResponse,
        feature_name="cv_visual_entry_header",
        prompt_version="3.3.0-logical-blocks",
        background_tasks=background_tasks,
        max_retries=CV_STRUCTURING_MAX_RETRIES,
        max_output_tokens=128,
        temperature=0.0,
        on_retry=on_retry,
    )
    response = LLMVisualEntryHeaderResponse.model_validate(value)
    if len(response.roles) != len(atoms):
        raise InvalidRangePlanError("visual header returned a role-count mismatch")
    roles = dict(zip(ordered_positions, response.roles, strict=True))
    for position, role in roles.items():
        text = section.content[position].text
        if (
            _LOCATION_RE.fullmatch(text)
            and _GEOGRAPHIC_TOKEN_RE.search(text)
            and role != "l"
        ):
            raise InvalidRangePlanError(
                "visual header mislabelled a geographic location"
            )
        if (
            re.search(r"(?:\b19|20)\d{2}|\b(?:present|current)\b", text, re.IGNORECASE)
            and role != "d"
        ):
            raise InvalidRangePlanError("visual header mislabelled a date")
    if "t" not in roles.values() or "o" not in roles.values():
        raise InvalidRangePlanError(
            "visual header requires both title and organization"
        )
    return roles


def _apply_visual_header_roles(
    compiled: list[_ResolvedBlock],
    section: _LedgerSection,
    roles: dict[int, str] | None,
) -> list[_ResolvedBlock]:
    """Replace only header field labels while retaining source ownership."""
    if not roles:
        return compiled
    header_atom_roles = {
        section.content[position].index: role for position, role in roles.items()
    }
    for index, block in enumerate(compiled):
        if block.kind != "e":
            continue
        owned_indexes = {atom.index for _, atoms in block.fields for atom in atoms}
        if not header_atom_roles.keys() <= owned_indexes:
            continue
        remaining_fields: list[tuple[str, list[SourceLedgerAtom]]] = []
        for role, atoms in block.fields:
            retained = [atom for atom in atoms if atom.index not in header_atom_roles]
            if retained:
                remaining_fields.append((role, retained))
        header_fields = [
            (role, [section.content[position]])
            for position, role in sorted(roles.items())
        ]
        return [
            *compiled[:index],
            _ResolvedBlock("e", [*header_fields, *remaining_fields]),
            *compiled[index + 1 :],
        ]
    raise InvalidRangePlanError("visual header atoms are not owned by an entry block")


async def _plan_section(
    section: _LedgerSection,
    *,
    index: int = 1,
    total_sections: int = 1,
    background_tasks: BackgroundTasks | None = None,
    on_retry: ParserRetryReporter | None = None,
) -> tuple[list[_ResolvedBlock], bool]:
    """Plan one section; returns ``(blocks, count_mismatch_clamped)``."""
    output_budget = CV_RANGE_PLAN_SECTION_MAX_OUTPUT_TOKENS
    header_positions = _visual_entry_header_positions(section)
    header_roles = (
        await _plan_visual_entry_header(
            section,
            header_positions,
            background_tasks=background_tasks,
            on_retry=on_retry,
        )
        if header_positions
        else None
    )
    system_prompt = build_section_range_plan_prompt(
        section.type,
        section.title.text,
        atom_count=len(section.content),
        has_visual_entry_header=bool(header_positions),
    )
    user_content = format_source_ledger(
        section.content,
        visual_entry_header_positions=header_positions,
    )

    # Log section details, the final system prompt, and formatted ledger to file
    _log_section_to_file(
        section,
        index,
        total_sections,
        system_prompt=system_prompt,
        user_content=user_content,
    )

    value = await call_llm_with_fallback(
        system_prompt,
        user_content,
        LLMSectionCursorPlanResponse,
        feature_name=f"cv_cursor_plan_{section.type}",
        prompt_version="3.3.0-logical-blocks",
        background_tasks=background_tasks,
        max_retries=CV_STRUCTURING_MAX_RETRIES,
        max_output_tokens=output_budget,
        temperature=0.0,
        on_retry=on_retry,
    )
    compiled, clamped = compile_section_cursor_plan(
        section,
        LLMSectionCursorPlanResponse.model_validate(value),
    )
    return _apply_visual_header_roles(compiled, section, header_roles), clamped


_logger = logging.getLogger(__name__)


def _log_section_to_file(
    section: _LedgerSection,
    index: int = 1,
    total_sections: int = 1,
    *,
    system_prompt: str | None = None,
    user_content: str | None = None,
) -> None:
    """Log section details, final system prompt, and ledger atoms to file before invoking the LLM cursor planner."""
    try:
        log_file = LOGS_DIR / "cv_range_plan_sections.log"
        now = datetime.now(timezone.utc).isoformat()

        atoms_preview = "\n".join(
            f"    [{atom.index}] (bullet={atom.is_bullet}) {atom.text}"
            for atom in section.content
        )
        system_prompt_str = system_prompt or build_section_range_plan_prompt(
            section.type, section.title.text
        )
        user_content_str = user_content or format_source_ledger(section.content)

        entry = (
            f"=== [{now}] SECTION {index}/{total_sections}: {section.type.upper()} ===\n"
            f"Title: {section.title.text} (index={section.title.index})\n"
            f"Atoms count: {len(section.content)}\n\n"
            f"--- FINAL SYSTEM PROMPT (build_section_range_plan_prompt) ---\n"
            f"{system_prompt_str}\n\n"
            f"--- USER CONTENT (format_source_ledger) ---\n"
            f"{user_content_str}\n\n"
            f"--- RAW LEDGER ATOMS ---\n"
            f"{atoms_preview}\n"
            f"{'=' * 70}\n\n"
        )

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)

        _logger.info(
            "Logged section [%d/%d] '%s' (%d atoms) and system prompt to %s",
            index,
            total_sections,
            section.type,
            len(section.content),
            log_file,
        )
    except Exception as err:
        _logger.warning("Failed to write section log to file: %s", err)


async def structure_cv_range_plan(
    *,
    cv_text: str,
    raw_extraction: RawExtraction | None = None,
    raw_extraction_ref_id: str | None = None,
    user_id: str | None = None,
    file_service: FileService | None = None,
    background_tasks: BackgroundTasks | None = None,
    on_retry: ParserRetryReporter | None = None,
) -> CVRangePlanResult:
    """Run V3.1 in isolation. Failed sections become explicit unknown content."""
    # -------------------------------------------------------------------------
    # 1. Resolve or validate the authoritative raw extraction and source text
    # -------------------------------------------------------------------------
    if raw_extraction is None:
        raw, source_text = await resolve_authoritative_source(
            cv_text=cv_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
            user_id=user_id,
            file_service=file_service,
        )
    else:
        validate_raw_extraction(raw_extraction)
        raw, source_text = raw_extraction, raw_extraction_to_text(raw_extraction)

    # -------------------------------------------------------------------------
    # 2. Build the server-owned source ledger
    # Deconstructs raw text blocks into indexed, atomic character fragments
    # (SourceLedgerAtoms) with coordinates and offsets.
    # -------------------------------------------------------------------------
    ledger = build_source_ledger(raw)

    try:
        # ---------------------------------------------------------------------
        # 3. Deterministically partition the ledger
        # Uses regex heading detection to split atoms into:
        # - preamble: atoms before the first section heading
        # - sections: list of _LedgerSection (heading atom + content atoms)
        # ---------------------------------------------------------------------
        preamble, sections = _partition_ledger(ledger)

        # ---------------------------------------------------------------------
        # 4. Deterministically extract candidate identity from the preamble
        # (Name, headline, email, phone, location, links) without LLM tokens.
        # 'assigned' tracks the set of ledger atom indexes consumed so far.
        # ---------------------------------------------------------------------
        identity, assigned = _build_identity(preamble)

        rendered_sections: list[CVSection] = []
        summary: CVParagraphBlock | None = None

        # Atoms in preamble that did not match any identity pattern
        unclassified = [atom for atom in preamble if atom.index not in assigned]
        section_failures: list[str] = []
        clamped_sections: list[str] = []

        # Mark all section heading and content atoms as owned/assigned
        for section in sections:
            assigned.add(section.title.index)
            assigned.update(atom.index for atom in section.content)

        # ---------------------------------------------------------------------
        # 5. Process sections concurrently through the range/cursor plan pipeline
        # ---------------------------------------------------------------------
        async def _process_section(
            index: int,
            section: _LedgerSection,
        ) -> tuple[
            int, _LedgerSection, list[Any], str | None, list[SourceLedgerAtom], bool
        ]:
            # Summary / Profile sections are handled deterministically without LLM calls
            if section.type == "summary" or not section.content:
                return index, section, [], None, [], False

            try:
                # Ask LLM for cursor plan (roles & counts) and compile against local section atoms
                compiled, clamped = await _plan_section(
                    section,
                    index=index,
                    total_sections=len(sections),
                    background_tasks=background_tasks,
                    on_retry=on_retry,
                )
                # Render compiled blocks into typed models (CVEntryBlock, CVBulletBlock, etc.)
                blocks = [
                    _render_block(
                        block,
                        block_id=f"range-plan-section-{index}-block-{block_index}",
                    )
                    for block_index, block in enumerate(compiled, start=1)
                ]
                return index, section, blocks, None, [], clamped
            except (HTTPException, InvalidRangePlanError, ValidationError) as exc:
                # Section-level fallback: if planning or validation fails for this section,
                # wrap content in a CVUnknownBlock rather than failing the whole CV.
                _logger.warning(
                    "Section [%d] '%s' cursor planning failed, falling back to unknown block: %s",
                    index,
                    section.type,
                    exc,
                )
                blocks = [_unknown_section_block(section)]
                return (
                    index,
                    section,
                    blocks,
                    section.type,
                    list(section.content),
                    False,
                )

        # Run all section planners in parallel
        section_results = await asyncio.gather(
            *[
                _process_section(index, section)
                for index, section in enumerate(sections, start=1)
            ]
        )

        for (
            index,
            section,
            blocks,
            failed_type,
            failed_atoms,
            clamped,
        ) in section_results:
            # Special case: Summary / Profile sections are rendered deterministically as paragraph
            if section.type == "summary":
                summary_block = CVParagraphBlock(
                    block_id="range-plan-summary",
                    text=_join(section.content) or "",
                    source_block_ids=_block_ids(section.content),
                )
                summary = summary_block
                rendered_sections.append(
                    CVSection(
                        id=f"range-plan-section-{index}",
                        type="summary",
                        title=section.title.text,
                        source_block_ids=[section.title.block_id],
                        blocks=[],
                    )
                )
                continue

            if failed_type:
                section_failures.append(failed_type)

            if clamped:
                _logger.warning(
                    "Section [%d] '%s' cursor plan counts clamped to section atoms",
                    index,
                    section.type,
                )
                clamped_sections.append(section.type)

            rendered_sections.append(
                CVSection(
                    id=f"range-plan-section-{index}",
                    type=section.type,
                    title=section.title.text,
                    source_block_ids=[section.title.block_id],
                    blocks=_normalize_skill_groups(blocks, section.type),
                )
            )

        # ---------------------------------------------------------------------
        # 6. Sanity check server ownership coverage (ensure no ledger atoms lost)
        # ---------------------------------------------------------------------
        assigned.update(atom.index for atom in unclassified)
        missing = sorted(set(range(len(ledger))) - assigned)
        if missing:
            raise InvalidRangePlanError(
                f"server ownership lost source atoms: {missing}"
            )

        # ---------------------------------------------------------------------
        # 8. Assemble full CVDocumentV2 and finalize cryptographic provenance hashes
        # ---------------------------------------------------------------------
        document = CVDocumentV2(
            raw_extraction_id=raw_extraction_ref_id,
            extraction_version=raw.extraction_version,
            parser_version="llm-cursor-plan-3.3-logical-blocks",
            source_hash=canonical_cv_hash(source_text),
            identity=identity,
            summary=summary,
            sections=rendered_sections,
        )
        document = finalize_document_provenance(raw, document)

        # If any atoms were unclassified or sections failed, record reconstruction warnings
        if unclassified or section_failures:
            document.reconstruction_warnings = list(
                dict.fromkeys(
                    [
                        *document.reconstruction_warnings,
                        "cursor_plan_unclassified_source",
                    ]
                )
            )

        # Clamped counts still render partial content, but the mismatch is
        # recorded loudly so miscounts are visible instead of silent.
        if clamped_sections:
            document.reconstruction_warnings = list(
                dict.fromkeys(
                    [
                        *document.reconstruction_warnings,
                        "cursor_plan_count_mismatch_clamped",
                    ]
                )
            )

        return CVRangePlanResult(
            raw,
            source_text,
            document,
            len(ledger),
            sorted({atom.index for atom in unclassified}),
            False,
            section_failures,
        )
    except (InvalidRangePlanError, ValidationError) as exc:
        _logger.exception("Global range plan fallback triggered: %s", exc)
        # ---------------------------------------------------------------------
        # Global Fallback: If range planning fails completely, fall back to
        # deterministic rule-based structuring.
        # ---------------------------------------------------------------------
        document = deterministic_structuring_fallback(
            raw=raw,
            source_text=source_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
        )
        return CVRangePlanResult(
            raw,
            source_text,
            document,
            len(ledger),
            [],
            True,
            [],
        )
