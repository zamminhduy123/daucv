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
)
from app.models.cv_range_plan import (
    LLMSectionCursorPlanResponse,
    LLMVisualEntryHeaderResponse,
    SourceLedgerAtom,
)
from app.models.cv_raw_extraction import RawExtraction
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
    raw_extraction_to_text,
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
    "skills": {"s", "x"},
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
    "u": {"t", "a", "v", "d", "q"},
    "d": {"i", "t", "m", "l", "d", "n"},
    "x": {"u"},
}
_REPEATABLE_ROLES = {"b", "k", "n", "u"}
_ENTRY_ANCHOR_BY_KIND = {"e": "t", "d": "i", "u": "t", "s": "g"}
_BULLET_PREFIX_RE = re.compile(r"^(?:[-–—•▪‣])\s*")


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
    """Build server-owned offset atoms; no durable IDs are sent to the model."""
    validate_raw_extraction(raw)
    ledger: list[SourceLedgerAtom] = []
    for page in raw.pages:
        for block in page.blocks:
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
                            page=page.page,
                            reading_order=block.reading_order,
                            bbox=block.bbox,
                            is_bullet=bool(_BULLET_PREFIX_RE.match(block.text)),
                            start_offset=start,
                            end_offset=end,
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
    return list(dict.fromkeys(atom.block_id for atom in atoms))


def _build_identity(preamble: list[SourceLedgerAtom]) -> tuple[CVIdentity, set[int]]:
    assigned: set[int] = set()
    values: dict[str, SourceLedgerAtom | None] = {
        key: None for key in ("name", "email", "phone", "location")
    }
    headline_atoms: list[SourceLedgerAtom] = []
    links: list[str] = []
    link_sources: dict[str, list[str]] = {}
    for offset, atom in enumerate(preamble):
        text = atom.text.strip()
        if not text:
            continue
        if _EMAIL_RE.search(text) and values["email"] is None:
            values["email"] = atom
        elif _PHONE_RE.search(text) and values["phone"] is None:
            values["phone"] = atom
        elif match := _LINK_RE.search(text):
            link = match.group(0).rstrip(".)]")
            links.append(link)
            link_sources[link] = [atom.block_id]
        elif _LOCATION_RE.fullmatch(text) and values["location"] is None:
            values["location"] = atom
        elif offset == 0 and values["name"] is None:
            values["name"] = atom
        elif (
            values["name"] is not None
            and not _EMAIL_RE.search(text)
            and not _PHONE_RE.search(text)
            and not _LINK_RE.search(text)
            and not (_LOCATION_RE.fullmatch(text) and _GEOGRAPHIC_TOKEN_RE.search(text))
        ):
            headline_atoms.append(atom)
        else:
            continue
        assigned.add(atom.index)

    def value(key: str, pattern: re.Pattern[str] | None = None) -> str | None:
        atom = values[key]
        if atom is None:
            return None
        match = pattern.search(atom.text) if pattern else None
        return match.group(0).rstrip(".)]") if match else atom.text

    def source(key: str) -> list[str]:
        return [values[key].block_id] if values[key] else []

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
) -> list[_ResolvedBlock]:
    """Consume the local ledger exactly once; cursor design prevents overlap."""
    cursor = 0
    compiled: list[_ResolvedBlock] = []
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

            # If cursor has already reached section end, skip any empty trailing segments
            if cursor >= len(section.content):
                break

            count = segment.count
            # For repeatable roles, clamp count so it never over-consumes past the end of section
            if segment.role in _REPEATABLE_ROLES:
                count = min(count, len(section.content) - cursor)
                # If this is the final segment of the final block, absorb all remaining section atoms
                is_final_segment = (
                    block_index == len(plan.blocks) - 1
                    and segment_index == len(block.segments) - 1
                )
                if is_final_segment:
                    count = len(section.content) - cursor

            end = cursor + count
            if end > len(section.content):
                if len(section.content) - cursor >= 1:
                    end = len(section.content)
                else:
                    raise InvalidRangePlanError(
                        f"segment {block_index}:{segment_index} consumes past section end"
                    )

            if end > cursor:
                fields.append((segment.role, section.content[cursor:end]))
                cursor = end

        if fields:
            compiled.extend(_split_repeated_anchor(_ResolvedBlock(block.kind, fields)))

    # If all blocks finished but some trailing atoms remain, absorb them into the last block
    if cursor < len(section.content) and compiled:
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
    return compiled


def _render_block(block: _ResolvedBlock, *, block_id: str):
    fields: dict[str, list[list[SourceLedgerAtom]]] = {}
    for role, atoms in block.fields:
        fields.setdefault(role, []).append(atoms)

    def single(role: str) -> str | None:
        groups = fields.get(role, [])
        return _join(groups[0]) if groups else None

    def multiple(role: str) -> list[str]:
        # For repeatable list roles, each source atom is its own item.
        # This ensures ["b", 3] → three bullet strings, not one merged string.
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
    """
    if section.type not in {"experience", "projects"}:
        return set()
    first_bullet = next(
        (
            index
            for index, atom in enumerate(section.content)
            if atom.is_bullet or _BULLET_PREFIX_RE.match(atom.text)
        ),
        len(section.content),
    )
    prefix = section.content[:first_bullet]
    if len(prefix) < 2 or any(atom.bbox is None for atom in prefix):
        return set()
    # Refuse broad prose prefixes. A compact, vertically adjacent group is a
    # reliable visual record header; later bullet text remains ordinary input.
    y_values = [atom.bbox[1] for atom in prefix if atom.bbox]
    if max(y_values) - min(y_values) > 36.0:
        return set()
    return set(range(len(prefix)))


async def _plan_visual_entry_header(
    section: _LedgerSection,
    positions: set[int],
    *,
    background_tasks: BackgroundTasks | None,
    on_retry: ParserRetryReporter | None,
) -> dict[int, str] | None:
    """Classify one small visual header independently from section planning."""
    ordered_positions = sorted(positions)
    atoms = [section.content[position] for position in ordered_positions]
    if not 2 <= len(atoms) <= 6:
        return None
    value = await call_llm_with_fallback(
        build_visual_entry_header_prompt(section.title.text),
        format_visual_entry_header(atoms),
        LLMVisualEntryHeaderResponse,
        feature_name="cv_visual_entry_header",
        prompt_version="3.2.0-experimental-geometry",
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
) -> list[_ResolvedBlock]:
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
        prompt_version="3.2.0-experimental-geometry",
        background_tasks=background_tasks,
        max_retries=CV_STRUCTURING_MAX_RETRIES,
        max_output_tokens=output_budget,
        temperature=0.0,
        on_retry=on_retry,
    )
    compiled = compile_section_cursor_plan(
        section,
        LLMSectionCursorPlanResponse.model_validate(value),
    )
    return _apply_visual_header_roles(compiled, section, header_roles)


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
        ) -> tuple[int, _LedgerSection, list[Any], str | None, list[SourceLedgerAtom]]:
            # Summary / Profile sections are handled deterministically without LLM calls
            if section.type == "summary" or not section.content:
                return index, section, [], None, []

            try:
                # Ask LLM for cursor plan (roles & counts) and compile against local section atoms
                compiled = await _plan_section(
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
                return index, section, blocks, None, []
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
                return index, section, blocks, section.type, list(section.content)

        # Run all section planners in parallel
        section_results = await asyncio.gather(
            *[
                _process_section(index, section)
                for index, section in enumerate(sections, start=1)
            ]
        )

        for index, section, blocks, failed_type, failed_atoms in section_results:
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
            parser_version="llm-cursor-plan-3.2-experimental-geometry",
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
