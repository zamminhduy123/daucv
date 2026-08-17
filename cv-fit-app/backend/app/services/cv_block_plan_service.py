"""Experimental v2 CV mapper: source atoms -> LLM plan -> exact CV document.

This module is deliberately not imported by routes or the existing mapper. It
is a shadowable adapter for evaluating small local models without trusting them
to reproduce candidate wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel, ValidationError

from app.core.config import (
    CV_BLOCK_PLAN_SECTION_MAX_OUTPUT_TOKENS,
    CV_STRUCTURING_MAX_RETRIES,
)
from app.models.cv_block_plan import (
    AtomBulletPlan,
    AtomEducationPlan,
    AtomEntryPlan,
    AtomIdentityPlan,
    AtomParagraphPlan,
    AtomPublicationPlan,
    AtomSectionPlan,
    AtomSkillGroupPlan,
    AtomUnknownPlan,
    LLMAtomBlockPlan,
    LLMAtomPlanResponse,
    LLMSectionAtomPlanResponse,
    SourceAtom,
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
from app.models.cv_raw_extraction import RawExtraction
from app.prompts.system_prompts import (
    build_section_block_plan_prompt,
    build_section_block_plan_repair_prompt,
    format_source_atoms,
)
from app.services.ai_service import call_llm_with_fallback
from app.services.cv_reconstruction_service import (
    InvalidSourceReferenceError,
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


class InvalidAtomPlanError(ValueError):
    """Raised when a plan references, repeats, or omits server-owned atoms."""


_ATOM_SPLIT_RE = re.compile(r"\s*(?:\||•|·)\s*")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
_LINK_RE = re.compile(
    r"(?:https?://|www\.)[^\s|•,;]+|(?:linkedin|github)\.com/[^\s|•,;]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CVBlockPlanResult:
    raw_extraction: RawExtraction
    source_text: str
    document: CVDocumentV2
    plan: LLMAtomPlanResponse | None
    atom_count: int
    repeated_atom_ids: list[str]
    unknown_atom_ids: list[str]
    missing_atom_ids: list[str]
    used_fallback: bool
    section_fallback_types: list[str]


@dataclass(frozen=True)
class _AtomSectionRange:
    type: str
    title_atom: SourceAtom
    content_atoms: list[SourceAtom]


@dataclass(frozen=True)
class _SectionPlanAudit:
    missing_atom_ids: list[str]
    repeated_atom_ids: list[str]
    unknown_atom_ids: list[str]
    coverage_missing_atom_ids: list[str]
    coverage_repeated_atom_ids: list[str]
    coverage_unknown_atom_ids: list[str]
    invalid_block_types: list[str]

    @property
    def requires_repair(self) -> bool:
        return any(
            (
                self.missing_atom_ids,
                self.repeated_atom_ids,
                self.unknown_atom_ids,
                self.coverage_missing_atom_ids,
                self.coverage_repeated_atom_ids,
                self.coverage_unknown_atom_ids,
                self.invalid_block_types,
            )
        )

    @property
    def issue_count(self) -> int:
        return sum(
            len(items)
            for items in (
                self.missing_atom_ids,
                self.repeated_atom_ids,
                self.unknown_atom_ids,
                self.coverage_missing_atom_ids,
                self.coverage_repeated_atom_ids,
                self.coverage_unknown_atom_ids,
                self.invalid_block_types,
            )
        )


_SECTION_BLOCK_TYPES: dict[str, set[str]] = {
    "education": {"education"},
    "skills": {"skill_group"},
    "publications": {"publication"},
    "certifications": {"entry"},
    "experience": {"entry", "bullet"},
    "projects": {"entry", "bullet"},
}


def build_source_atoms(raw: RawExtraction) -> list[SourceAtom]:
    """Create deterministic line/separator atoms without asking an LLM to split text."""
    validate_raw_extraction(raw)
    atoms: list[SourceAtom] = []
    for page in raw.pages:
        for block in page.blocks:
            fragments: list[str] = []
            for line in block.text.splitlines() or [block.text]:
                fragments.extend(
                    fragment.strip()
                    for fragment in _ATOM_SPLIT_RE.split(line)
                    if fragment.strip()
                )
            if not fragments and block.text.strip():
                fragments = [block.text.strip()]
            for ordinal, fragment in enumerate(fragments):
                text = normalize_grounding_text(fragment)
                if not text:
                    continue
                atoms.append(
                    SourceAtom(
                        # IDs are model-facing pointers, not integrity tokens.
                        # Raw block IDs are already unique; adding a hash made
                        # small models reproduce an otherwise correct pointer
                        # with one fabricated character in the suffix.
                        atom_id=f"{block.block_id}:a{ordinal + 1}",
                        block_id=block.block_id,
                        text=text,
                        page=page.page,
                        reading_order=block.reading_order,
                        ordinal=ordinal,
                    )
                )
    if not atoms:
        raise InvalidAtomPlanError("Raw extraction contains no usable source atoms")
    return atoms


def validate_atom_plan(atoms: list[SourceAtom], plan: LLMAtomPlanResponse) -> None:
    """Require complete use of known atoms; repeated references remain auditable."""
    known_ids = {atom.atom_id for atom in atoms}
    referenced_ids = plan.referenced_atom_ids()
    unknown = referenced_ids - known_ids
    if unknown:
        raise InvalidAtomPlanError(
            f"Block-plan mapper referenced unknown source atoms: {sorted(unknown)}"
        )
    missing = known_ids - referenced_ids
    if missing:
        raise InvalidAtomPlanError(
            f"Block-plan mapper omitted source atoms: {sorted(missing)}"
        )


def _unknown_atom_ids(atoms: list[SourceAtom], plan: LLMAtomPlanResponse) -> list[str]:
    known_ids = {atom.atom_id for atom in atoms}
    return sorted(plan.referenced_atom_ids() - known_ids)


def _missing_atom_ids(atoms: list[SourceAtom], plan: LLMAtomPlanResponse) -> list[str]:
    known_ids = {atom.atom_id for atom in atoms}
    return sorted(known_ids - plan.referenced_atom_ids())


def _drop_unknown_atom_references(
    plan: BaseModel,
    known_ids: set[str],
) -> BaseModel:
    """Remove forged pointers after schema parsing, preserving valid assignments.

    Plan coverage is an experimental quality metric, not a reason to discard a
    source-safe partial parse. Required plan lists can become empty here; the
    adapter renders those fields as empty and marks the result non-exportable.
    """
    sanitized = plan.model_copy(deep=True)

    def walk(value: object) -> None:
        if isinstance(value, BaseModel):
            for name in type(value).model_fields:
                child = getattr(value, name)
                if name.endswith("_atom_ids") and isinstance(child, list):
                    setattr(
                        value,
                        name,
                        [atom_id for atom_id in child if atom_id in known_ids],
                    )
                elif name.endswith("_atom_id_groups") and isinstance(child, list):
                    setattr(
                        value,
                        name,
                        [
                            [atom_id for atom_id in group if atom_id in known_ids]
                            for group in child
                            if any(atom_id in known_ids for atom_id in group)
                        ],
                    )
                else:
                    walk(child)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(sanitized)
    return sanitized


def _validate_known_atom_references(
    atoms: list[SourceAtom],
    plan: LLMAtomPlanResponse,
) -> None:
    if unknown := _unknown_atom_ids(atoms, plan):
        raise InvalidAtomPlanError(
            f"Block-plan mapper referenced unknown source atoms: {unknown}"
        )


def repeated_atom_ids(plan: LLMAtomPlanResponse) -> list[str]:
    """Return duplicate semantic references without throwing away valid JSON."""
    ids = [
        *plan.identity.referenced_atom_ids(),
        *plan.summary_atom_ids,
        *(
            atom_id
            for section in plan.sections
            for atom_id in section.referenced_atom_ids()
        ),
    ]
    counts: dict[str, int] = {}
    for atom_id in ids:
        counts[atom_id] = counts.get(atom_id, 0) + 1
    return sorted(atom_id for atom_id, count in counts.items() if count > 1)


def _unknown_section_block(atoms: list[SourceAtom]) -> AtomUnknownPlan | None:
    """Preserve an unavailable local range without pretending it was parsed."""
    if not atoms:
        return None
    return AtomUnknownPlan(
        type="unknown", line_atom_ids=[atom.atom_id for atom in atoms], confidence=0.0
    )


def _repeated_ids(atom_ids: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for atom_id in atom_ids:
        counts[atom_id] = counts.get(atom_id, 0) + 1
    return sorted(atom_id for atom_id, count in counts.items() if count > 1)


def _audit_section_plan(
    *,
    section_type: str,
    atoms: list[SourceAtom],
    plan: LLMSectionAtomPlanResponse,
) -> _SectionPlanAudit:
    """Check semantic ownership and model-provided coverage independently."""
    known_ids = [atom.atom_id for atom in atoms]
    known_set = set(known_ids)
    semantic_ids = [
        atom_id for block in plan.blocks for atom_id in block.referenced_atom_ids()
    ]
    semantic_set = set(semantic_ids)
    coverage_set = set(plan.coverage_atom_ids)
    allowed = _SECTION_BLOCK_TYPES.get(section_type)
    invalid_block_types = sorted(
        {
            block.type
            for block in plan.blocks
            if allowed is not None and block.type not in allowed
        }
    )
    return _SectionPlanAudit(
        missing_atom_ids=sorted(known_set - semantic_set),
        repeated_atom_ids=_repeated_ids(semantic_ids),
        unknown_atom_ids=sorted(semantic_set - known_set),
        coverage_missing_atom_ids=sorted(known_set - coverage_set),
        coverage_repeated_atom_ids=_repeated_ids(plan.coverage_atom_ids),
        coverage_unknown_atom_ids=sorted(coverage_set - known_set),
        invalid_block_types=invalid_block_types,
    )


def _deterministic_identity_plan(atoms: list[SourceAtom]) -> AtomIdentityPlan:
    """Assign CV header fields without requiring an LLM pointer plan."""
    plan = AtomIdentityPlan()
    for index, atom in enumerate(atoms):
        if index == 0:
            plan.full_name_atom_ids = [atom.atom_id]
        elif index == 1:
            plan.headline_atom_ids = [atom.atom_id]
        if _EMAIL_RE.search(atom.text):
            plan.email_atom_ids.append(atom.atom_id)
        if _PHONE_RE.search(atom.text):
            plan.phone_atom_ids.append(atom.atom_id)
        if _LINK_RE.search(atom.text) or atom.text.casefold() in {
            "linkedin",
            "github",
            "website",
            "google scholar",
        }:
            plan.link_atom_id_groups.append([atom.atom_id])
    return plan


def split_atoms_into_sections(
    atoms: list[SourceAtom],
) -> tuple[AtomIdentityPlan, list[SourceAtom], list[_AtomSectionRange]]:
    """Partition atoms by deterministic known headings before LLM calls."""
    headings = [
        (index, classified[0])
        for index, atom in enumerate(atoms)
        if (classified := classify_heading(atom.text)) is not None
    ]
    if not headings:
        raise InvalidAtomPlanError("No deterministic CV section headings found")
    first_heading_index = headings[0][0]
    preamble = atoms[:first_heading_index]
    ranges: list[_AtomSectionRange] = []
    for range_index, (start, section_type) in enumerate(headings):
        end = (
            headings[range_index + 1][0]
            if range_index + 1 < len(headings)
            else len(atoms)
        )
        ranges.append(
            _AtomSectionRange(
                type=section_type,
                title_atom=atoms[start],
                content_atoms=atoms[start + 1 : end],
            )
        )
    return _deterministic_identity_plan(preamble), preamble, ranges


def _atom_text(atom_ids: list[str], atom_map: dict[str, SourceAtom]) -> str | None:
    if not atom_ids:
        return None
    return " ".join(atom_map[atom_id].text for atom_id in atom_ids)


def _block_ids(atom_ids: list[str], atom_map: dict[str, SourceAtom]) -> list[str]:
    return list(dict.fromkeys(atom_map[atom_id].block_id for atom_id in atom_ids))


def _identity_value(
    atom_ids: list[str],
    atom_map: dict[str, SourceAtom],
    pattern: re.Pattern[str] | None = None,
) -> str | None:
    value = _atom_text(atom_ids, atom_map)
    if not value:
        return None
    if pattern:
        match = pattern.search(value)
        return match.group(0).rstrip(".)]") if match else None
    return value


def _server_block(
    plan: LLMAtomBlockPlan,
    *,
    block_id: str,
    atom_map: dict[str, SourceAtom],
):
    source_atom_ids = plan.referenced_atom_ids()
    common = {
        "block_id": block_id,
        "confidence": plan.confidence,
        "source_block_ids": _block_ids(source_atom_ids, atom_map),
    }
    if isinstance(plan, AtomEntryPlan):
        return CVEntryBlock(
            **common,
            title=_atom_text(plan.title_atom_ids, atom_map) or "",
            subtitle=_atom_text(plan.subtitle_atom_ids, atom_map),
            organization=_atom_text(plan.organization_atom_ids, atom_map),
            location=_atom_text(plan.location_atom_ids, atom_map),
            date=_atom_text(plan.date_atom_ids, atom_map),
            bullets=[
                _atom_text(group, atom_map) or ""
                for group in plan.bullet_atom_id_groups
            ],
        )
    if isinstance(plan, AtomBulletPlan):
        return CVBulletBlock(
            **common, text=_atom_text(plan.text_atom_ids, atom_map) or ""
        )
    if isinstance(plan, AtomParagraphPlan):
        return CVParagraphBlock(
            **common, text=_atom_text(plan.text_atom_ids, atom_map) or ""
        )
    if isinstance(plan, AtomSkillGroupPlan):
        return CVSkillGroupBlock(
            **common,
            label=_atom_text(plan.label_atom_ids, atom_map),
            skills=[
                _atom_text(group, atom_map) or "" for group in plan.skill_atom_id_groups
            ],
        )
    if isinstance(plan, AtomPublicationPlan):
        return CVPublicationBlock(
            **common,
            title=_atom_text(plan.title_atom_ids, atom_map) or "",
            authors=_atom_text(plan.authors_atom_ids, atom_map),
            venue=_atom_text(plan.venue_atom_ids, atom_map),
            date=_atom_text(plan.date_atom_ids, atom_map),
            status=_atom_text(plan.status_atom_ids, atom_map),
        )
    if isinstance(plan, AtomEducationPlan):
        return CVEducationBlock(
            **common,
            institution=_atom_text(plan.institution_atom_ids, atom_map),
            degree=_atom_text(plan.degree_atom_ids, atom_map),
            field=_atom_text(plan.field_atom_ids, atom_map),
            location=_atom_text(plan.location_atom_ids, atom_map),
            date=_atom_text(plan.date_atom_ids, atom_map),
            details=[
                _atom_text(group, atom_map) or ""
                for group in plan.detail_atom_id_groups
            ],
        )
    if isinstance(plan, AtomUnknownPlan):
        return CVUnknownBlock(
            **common,
            lines=[
                _atom_text([atom_id], atom_map) or "" for atom_id in plan.line_atom_ids
            ],
        )
    raise TypeError(f"Unsupported block plan: {type(plan).__name__}")


def assemble_block_plan_document(
    *,
    raw: RawExtraction,
    plan: LLMAtomPlanResponse,
    source_text: str,
    raw_extraction_ref_id: str | None,
) -> CVDocumentV2:
    """Adapt validated atom references into a normal CVDocumentV2."""
    atoms = build_source_atoms(raw)
    _validate_known_atom_references(atoms, plan)
    atom_map = {atom.atom_id: atom for atom in atoms}
    identity_plan = plan.identity
    links: list[str] = []
    link_sources: dict[str, list[str]] = {}
    for group in identity_plan.link_atom_id_groups:
        value = _identity_value(group, atom_map, _LINK_RE)
        if value and value not in link_sources:
            links.append(value)
            link_sources[value] = _block_ids(group, atom_map)
    identity = CVIdentity(
        full_name=_identity_value(identity_plan.full_name_atom_ids, atom_map),
        headline=_identity_value(identity_plan.headline_atom_ids, atom_map),
        email=_identity_value(identity_plan.email_atom_ids, atom_map, _EMAIL_RE),
        phone=_identity_value(identity_plan.phone_atom_ids, atom_map, _PHONE_RE),
        location=_identity_value(identity_plan.location_atom_ids, atom_map),
        links=links,
        field_source_block_ids=CVIdentitySourceMap(
            full_name=_block_ids(identity_plan.full_name_atom_ids, atom_map),
            headline=_block_ids(identity_plan.headline_atom_ids, atom_map),
            email=_block_ids(identity_plan.email_atom_ids, atom_map),
            phone=_block_ids(identity_plan.phone_atom_ids, atom_map),
            location=_block_ids(identity_plan.location_atom_ids, atom_map),
            links=link_sources,
        ),
    )
    summary = None
    if plan.summary_atom_ids:
        summary = CVParagraphBlock(
            block_id="block-plan-summary",
            text=_atom_text(plan.summary_atom_ids, atom_map) or "",
            source_block_ids=_block_ids(plan.summary_atom_ids, atom_map),
        )
    sections: list[CVSection] = []
    for section_index, section_plan in enumerate(plan.sections, start=1):
        section_id = f"block-plan-section-{section_index}"
        sections.append(
            CVSection(
                id=section_id,
                type=section_plan.type,
                title=_atom_text(section_plan.title_atom_ids, atom_map) or "",
                confidence=section_plan.confidence,
                source_block_ids=_block_ids(section_plan.title_atom_ids, atom_map),
                blocks=[
                    _server_block(
                        block_plan,
                        block_id=f"{section_id}-block-{block_index}",
                        atom_map=atom_map,
                    )
                    for block_index, block_plan in enumerate(
                        section_plan.blocks, start=1
                    )
                ],
            )
        )
    document = CVDocumentV2(
        raw_extraction_id=raw_extraction_ref_id,
        extraction_version=raw.extraction_version,
        parser_version="llm-block-plan-2.0-experimental",
        requires_reprocessing=False,
        source_hash=canonical_cv_hash(source_text),
        identity=identity,
        summary=summary,
        sections=sections,
    )
    return finalize_document_provenance(raw, document)


async def structure_cv_block_plan(
    *,
    cv_text: str,
    raw_extraction: RawExtraction | None = None,
    raw_extraction_ref_id: str | None = None,
    user_id: str | None = None,
    file_service: FileService | None = None,
    background_tasks: BackgroundTasks | None = None,
    on_retry: ParserRetryReporter | None = None,
) -> CVBlockPlanResult:
    """Run isolated v2 mapping. Existing LLM1 callers never pass this seam."""
    if raw_extraction is None:
        raw, source_text = await resolve_authoritative_source(
            cv_text=cv_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
            user_id=user_id,
            file_service=file_service,
        )
    else:
        validate_raw_extraction(raw_extraction)
        raw = raw_extraction
        source_text = raw_extraction_to_text(raw)
    atoms = build_source_atoms(raw)

    try:
        identity, _preamble, ranges = split_atoms_into_sections(atoms)
        sections: list[AtomSectionPlan] = []
        summary_atom_ids: list[str] = []
        section_fallback_types: list[str] = []

        for section_range in ranges:
            # Summary content needs no semantic grouping. Keep it deterministic
            # and preserve its heading as a source-owned empty section.
            if section_range.type == "summary":
                summary_atom_ids.extend(
                    atom.atom_id for atom in section_range.content_atoms
                )
                sections.append(
                    AtomSectionPlan(
                        type=section_range.type,
                        title_atom_ids=[section_range.title_atom.atom_id],
                    )
                )
                continue

            local_blocks: list[LLMAtomBlockPlan] = []
            if section_range.content_atoms:
                local_known_ids = {atom.atom_id for atom in section_range.content_atoms}
                try:
                    value = await call_llm_with_fallback(
                        build_section_block_plan_prompt(
                            section_range.type,
                            section_range.title_atom.text,
                        ),
                        format_source_atoms(section_range.content_atoms),
                        LLMSectionAtomPlanResponse,
                        feature_name=f"cv_block_plan_{section_range.type}",
                        prompt_version="2.2.0-experimental-staged",
                        background_tasks=background_tasks,
                        max_retries=CV_STRUCTURING_MAX_RETRIES,
                        max_output_tokens=CV_BLOCK_PLAN_SECTION_MAX_OUTPUT_TOKENS,
                        temperature=0.0,
                        on_retry=on_retry,
                    )
                    raw_section = LLMSectionAtomPlanResponse.model_validate(value)
                    audit = _audit_section_plan(
                        section_type=section_range.type,
                        atoms=section_range.content_atoms,
                        plan=raw_section,
                    )
                    if audit.requires_repair:
                        try:
                            repaired_value = await call_llm_with_fallback(
                                build_section_block_plan_repair_prompt(
                                    section_range.type,
                                    section_title=section_range.title_atom.text,
                                    missing_atom_ids=audit.missing_atom_ids,
                                    repeated_atom_ids=audit.repeated_atom_ids,
                                    invalid_block_types=audit.invalid_block_types,
                                ),
                                format_source_atoms(section_range.content_atoms),
                                LLMSectionAtomPlanResponse,
                                feature_name=f"cv_block_plan_{section_range.type}_repair",
                                prompt_version="2.2.0-experimental-staged-repair",
                                background_tasks=background_tasks,
                                max_retries=CV_STRUCTURING_MAX_RETRIES,
                                max_output_tokens=CV_BLOCK_PLAN_SECTION_MAX_OUTPUT_TOKENS,
                                temperature=0.0,
                                on_retry=on_retry,
                            )
                            repaired_section = (
                                LLMSectionAtomPlanResponse.model_validate(
                                    repaired_value
                                )
                            )
                            repaired_audit = _audit_section_plan(
                                section_type=section_range.type,
                                atoms=section_range.content_atoms,
                                plan=repaired_section,
                            )
                            if repaired_audit.issue_count < audit.issue_count:
                                raw_section = repaired_section
                        except (HTTPException, InvalidAtomPlanError, ValidationError):
                            # The original plan remains source-safe after the
                            # later sanitization step and will be marked by its
                            # final coverage audit if still incomplete.
                            pass
                    section_plan = _drop_unknown_atom_references(
                        raw_section,
                        local_known_ids,
                    )
                    assert isinstance(section_plan, LLMSectionAtomPlanResponse)
                    local_blocks = section_plan.blocks
                except (HTTPException, InvalidAtomPlanError, ValidationError):
                    fallback_block = _unknown_section_block(section_range.content_atoms)
                    if fallback_block:
                        local_blocks = [fallback_block]
                    section_fallback_types.append(section_range.type)

            sections.append(
                AtomSectionPlan(
                    type=section_range.type,
                    title_atom_ids=[section_range.title_atom.atom_id],
                    blocks=local_blocks,
                )
            )

        raw_plan = LLMAtomPlanResponse(
            identity=identity,
            summary_atom_ids=summary_atom_ids,
            sections=sections,
        )
        known_ids = {atom.atom_id for atom in atoms}
        unknown = _unknown_atom_ids(atoms, raw_plan)
        plan = _drop_unknown_atom_references(raw_plan, known_ids)
        assert isinstance(plan, LLMAtomPlanResponse)
        missing = _missing_atom_ids(atoms, plan)
        document = assemble_block_plan_document(
            raw=raw,
            plan=plan,
            source_text=source_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
        )
        duplicates = repeated_atom_ids(plan)
        if duplicates or unknown or missing or section_fallback_types:
            # This experimental result is useful for structural comparison but
            # must never become exportable while a source fragment appears in
            # multiple visible semantic fields.
            document.requires_reprocessing = True
            document.reconstruction_warnings = list(
                dict.fromkeys(
                    [
                        *document.reconstruction_warnings,
                        *(
                            ["block_plan_duplicate_atom_reference"]
                            if duplicates
                            else []
                        ),
                        *(["block_plan_unknown_atom_reference"] if unknown else []),
                        *(["block_plan_missing_atom_reference"] if missing else []),
                        *(
                            ["block_plan_section_fallback"]
                            if section_fallback_types
                            else []
                        ),
                    ]
                )
            )
        return CVBlockPlanResult(
            raw,
            source_text,
            document,
            plan,
            len(atoms),
            duplicates,
            unknown,
            missing,
            bool(section_fallback_types),
            section_fallback_types,
        )
    except (
        HTTPException,
        InvalidSourceReferenceError,
        InvalidAtomPlanError,
        ValidationError,
    ):
        document = deterministic_structuring_fallback(
            raw=raw,
            source_text=source_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
        )
        return CVBlockPlanResult(
            raw,
            source_text,
            document,
            None,
            len(atoms),
            [],
            [],
            [],
            True,
            [],
        )
