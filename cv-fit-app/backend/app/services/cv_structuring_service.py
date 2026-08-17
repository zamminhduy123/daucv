"""Authoritative source resolution and LLM semantic CV structuring."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

from fastapi import BackgroundTasks, HTTPException

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
    LLMUnmappedReference,
)
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    InvalidRawExtractionArtifactError,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.models.cv_structuring import LLMSemanticBlock, LLMSemanticCVResponse
from app.prompts.system_prompts import (
    format_raw_extraction_blocks,
)
from app.services.cv_reconstruction_service import (
    InvalidSourceReferenceError,
    canonical_cv_hash,
    finalize_document_provenance,
    reconstruct_from_lines,
)
from app.services.cv_source_grounding import (
    normalize_grounding_text as _normalize_grounding_text,
)
from app.services.files import FileService
from app.services.layout_extraction import (
    raw_extraction_to_layout_lines,
    raw_extraction_to_text,
    validate_raw_extraction,
)

_logger = logging.getLogger(__name__)

ParserRetryReporter = Callable[[int, int], Awaitable[None]]


@dataclass(frozen=True)
class CVStructuringResult:
    raw_extraction: RawExtraction
    source_text: str
    document: CVDocumentV2
    used_fallback: bool


class SemanticGroundingError(ValueError):
    """A parser field could not be grounded in only its cited source blocks."""

    def __init__(self, field_path: str, reason: str) -> None:
        self.field_path = field_path
        self.reason = reason
        super().__init__(f"Semantic grounding failed at {field_path}: {reason}")


def build_manual_text_extraction(cv_text: str) -> RawExtraction:
    """Build deterministic source blocks for authoritative pasted/manual text."""
    blocks: list[RawBlock] = []
    for raw_line in (line.strip() for line in cv_text.splitlines()):
        if not raw_line:
            continue
        blocks.append(
            RawBlock(
                # Model-facing source IDs must be easy to reproduce exactly.
                # Content hashes make a small model fabricate one suffix
                # character and turn an otherwise grounded response into a
                # provenance failure. IDs are scoped to this raw extraction,
                # so sequential pointers remain unique and authoritative.
                block_id=f"manual-p1-b{len(blocks) + 1}",
                page=1,
                text=raw_line,
                extraction_method=ExtractionMethod.MANUAL_TEXT,
                reading_order=len(blocks),
                confidence=1.0,
            )
        )
    raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[RawPage(page=1, blocks=blocks)],
    )
    validate_raw_extraction(raw)
    return raw


def _normalized_source_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def source_text_materially_disagrees(submitted: str, authoritative: str) -> bool:
    """Return True for meaningful edits, while tolerating layout whitespace drift."""
    left = _normalized_source_text(submitted)
    right = _normalized_source_text(authoritative)
    if not left or left == right:
        return False
    return SequenceMatcher(None, left, right, autojunk=False).ratio() < 0.98


async def resolve_authoritative_source(
    *,
    cv_text: str,
    raw_extraction_ref_id: str | None,
    user_id: str | None,
    file_service: FileService | None,
) -> tuple[RawExtraction, str]:
    """Resolve PDF references server-side or build manual-text source blocks."""
    if raw_extraction_ref_id:
        if not user_id or file_service is None:
            raise HTTPException(
                status_code=500,
                detail="Raw extraction service is unavailable.",
            )
        try:
            raw = await file_service.load_raw_extraction(
                user_id,
                raw_extraction_ref_id,
            )
        except InvalidRawExtractionArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail="Raw extraction artifact is invalid.",
            ) from exc
        if raw is None:
            raise HTTPException(
                status_code=404,
                detail="Raw extraction reference was not found.",
            )
        validate_raw_extraction(raw)
        authoritative_text = raw_extraction_to_text(raw)
        if cv_text.strip() and source_text_materially_disagrees(
            cv_text,
            authoritative_text,
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Submitted CV text no longer matches the uploaded PDF source. "
                    "Remove the stale upload reference or re-upload the CV."
                ),
            )
        return raw, authoritative_text

    if not cv_text.strip():
        raise HTTPException(status_code=422, detail="Cần cung cấp nội dung CV.")
    return build_manual_text_extraction(cv_text), cv_text.strip()


def validate_parser_source_references(
    raw: RawExtraction,
    response: LLMSemanticCVResponse,
) -> None:
    """Reject unknown/forged IDs and mapped/unmapped ownership conflicts."""
    validate_raw_extraction(raw)
    known_ids = {block.block_id for page in raw.pages for block in page.blocks}
    referenced_ids = response.referenced_source_block_ids()
    unknown_ids = referenced_ids - known_ids
    if unknown_ids:
        raise InvalidSourceReferenceError(
            "Semantic parser referenced unknown block IDs"
        )

    unmapped_ids = {item.block_id for item in response.unmapped_references}
    mapped_ids = response.mapped_source_block_ids()
    if mapped_ids & unmapped_ids:
        raise InvalidSourceReferenceError(
            "Semantic parser mapped and unmapped the same source block"
        )


def discard_redundant_unmapped_references(response: LLMSemanticCVResponse) -> None:
    """Mapped ownership wins over a redundant model-supplied unmapped marker.

    An `unmapped_references` item is only metadata; retaining it alongside a
    valid mapped use of the same source block creates a false ownership
    conflict. Dropping that redundant marker preserves all candidate-visible
    content and lets normal grounding and coverage checks remain authoritative.
    """
    mapped_ids = response.mapped_source_block_ids()
    redundant_ids = {
        item.block_id
        for item in response.unmapped_references
        if item.block_id in mapped_ids
    }
    if not redundant_ids:
        return
    response.unmapped_references = [
        item
        for item in response.unmapped_references
        if item.block_id not in redundant_ids
    ]
    _logger.info(
        "Discarded redundant unmapped references for mapped source blocks: %s",
        sorted(redundant_ids),
    )


def _ordered_raw_blocks(raw: RawExtraction) -> list[RawBlock]:
    indexed_blocks = [
        (page.page, block.reading_order, page_index, block_index, block)
        for page_index, page in enumerate(raw.pages)
        for block_index, block in enumerate(page.blocks)
    ]
    indexed_blocks.sort(key=lambda item: item[:4])
    return [item[4] for item in indexed_blocks]


def _source_text_for_ids(raw: RawExtraction, source_ids: list[str]) -> str:
    selected = set(source_ids)
    return "\n".join(
        block.text for block in _ordered_raw_blocks(raw) if block.block_id in selected
    )


def _require_grounded_text(
    raw: RawExtraction,
    *,
    value: str | None,
    source_ids: list[str],
    field_path: str,
) -> None:
    if value is None:
        return
    normalized_value = _normalize_grounding_text(value)
    if not normalized_value:
        raise SemanticGroundingError(field_path, "empty_value")
    normalized_source = _normalize_grounding_text(_source_text_for_ids(raw, source_ids))
    if not normalized_source or normalized_value not in normalized_source:
        raise SemanticGroundingError(field_path, "not_in_cited_source")


def validate_semantic_grounding(
    raw: RawExtraction,
    response: LLMSemanticCVResponse,
) -> None:
    """Require every parser-authored textual leaf to exist in its cited source."""
    validate_parser_source_references(raw, response)
    from app.services.cv_source_grounding import iter_semantic_text_leaves

    for leaf in iter_semantic_text_leaves(response):
        _require_grounded_text(
            raw,
            value=leaf.value,
            source_ids=leaf.source_block_ids,
            field_path=leaf.field_path,
        )


def _exact_source_ids_for_value(raw: RawExtraction, value: str) -> list[str]:
    """Find the smallest ordered source-block range containing ``value`` exactly."""
    normalized_value = _normalize_grounding_text(value)
    if not normalized_value:
        return []

    blocks = _ordered_raw_blocks(raw)
    for block in blocks:
        if normalized_value in _normalize_grounding_text(block.text):
            return [block.block_id]

    # PDF layout can split a bullet across several independently positioned
    # blocks. Prefer the smallest *exact* ordered range, while allowing a
    # complete wrapped bullet to span a modest part of a page.
    for span_size in range(2, min(len(blocks), 16) + 1):
        for index in range(len(blocks) - span_size + 1):
            end_index = index + span_size - 1
            combined = _normalize_grounding_text(
                "\n".join(item.text for item in blocks[index : end_index + 1])
            )
            if normalized_value in combined:
                return [item.block_id for item in blocks[index : end_index + 1]]
    return []


def _repair_near_verbatim_bullet(
    raw: RawExtraction,
    response: LLMSemanticCVResponse,
    error: SemanticGroundingError,
) -> bool:
    """Replace a near-verbatim entry bullet with its cited source wording.

    Smaller local models occasionally change punctuation, morphology, or a
    single verb despite being asked to copy verbatim. This repair is purposely
    narrow: it applies only to bullets and only selects one cited source line
    with an extremely high textual-similarity score. The repaired value still
    has to pass the normal exact grounding gate immediately afterwards.
    """
    match = re.fullmatch(
        r"sections\[(\d+)\]\.blocks\[(\d+)\]\.bullets\[(\d+)\]",
        error.field_path,
    )
    if not match:
        return False

    section_index, block_index, bullet_index = (int(value) for value in match.groups())
    try:
        block = response.sections[section_index].blocks[block_index]
        candidate = block.bullets[bullet_index]
    except (AttributeError, IndexError):
        return False

    normalized_candidate = _normalize_grounding_text(candidate)
    if not normalized_candidate:
        return False

    source_map = {
        source_block.block_id: source_block for source_block in _ordered_raw_blocks(raw)
    }
    best: tuple[float, str, str] | None = None
    for source_id in block.source_block_ids:
        source_block = source_map.get(source_id)
        if source_block is None:
            continue
        for line in source_block.text.splitlines() or [source_block.text]:
            normalized_line = _normalize_grounding_text(line)
            if not normalized_line:
                continue
            score = SequenceMatcher(
                None,
                normalized_candidate,
                normalized_line,
                autojunk=False,
            ).ratio()
            if best is None or score > best[0]:
                best = (score, source_id, normalized_line)

    # 0.92 permits tiny punctuation/spacing drift but rejects paraphrases.
    if best is None or best[0] < 0.92:
        return False

    _, source_id, source_text = best
    block.bullets[bullet_index] = source_text
    block.source_block_ids = list(dict.fromkeys([*block.source_block_ids, source_id]))
    _logger.info(
        "Recovered near-verbatim source bullet at %s (similarity=%.3f)",
        error.field_path,
        best[0],
    )
    return True


def _repair_summary_from_cited_source(
    raw: RawExtraction,
    response: LLMSemanticCVResponse,
    error: SemanticGroundingError,
) -> bool:
    """Restore a paraphrased summary from the PDF blocks it already cites.

    A summary is a free-form paragraph, so a small mapper can paraphrase an
    otherwise correctly selected group of source blocks.  Unlike an entry
    bullet, there is no safe similarity threshold for reconstructing it.
    Replacing the value with the cited block text is deterministic and keeps
    the final content exactly within the authoritative source.
    """
    if error.field_path != "summary.text" or response.summary is None:
        return False

    source_ids = response.summary.source_block_ids
    # A summary may reasonably span a handful of wrapped PDF blocks.  Do not
    # turn an accidentally broad citation into a giant summary paragraph.
    if not 1 <= len(source_ids) <= 8:
        return False

    source_text = _normalize_grounding_text(_source_text_for_ids(raw, source_ids))
    if not source_text:
        return False

    response.summary.text = source_text
    _logger.info(
        "Recovered summary from %d cited source blocks",
        len(source_ids),
    )
    return True


def _repair_missing_block_citation(
    raw: RawExtraction,
    response: LLMSemanticCVResponse,
    error: SemanticGroundingError,
) -> bool:
    """Repair only an omitted citation when its exact value exists in source."""
    identity_link_match = re.fullmatch(r"identity\.links\[(\d+)\]", error.field_path)
    if identity_link_match:
        link_index = int(identity_link_match.group(1))
        try:
            link = response.identity.links[link_index]
        except IndexError:
            return False
        recovered_ids = _exact_source_ids_for_value(raw, link)
        if not recovered_ids:
            return False
        response.identity.field_source_block_ids.links[link] = recovered_ids
        _logger.info(
            "Repaired exact source citation for %s with block IDs %s",
            error.field_path,
            recovered_ids,
        )
        return True

    match = re.fullmatch(
        r"sections\[(\d+)\]\.blocks\[(\d+)\](?:\..+)?", error.field_path
    )
    if not match:
        return False

    section_index, block_index = (int(value) for value in match.groups())
    try:
        block = response.sections[section_index].blocks[block_index]
    except IndexError:
        return False

    from app.services.cv_source_grounding import iter_semantic_text_leaves

    leaf = next(
        (
            candidate
            for candidate in iter_semantic_text_leaves(response)
            if candidate.field_path == error.field_path
        ),
        None,
    )
    if leaf is None:
        return False

    recovered_ids = _exact_source_ids_for_value(raw, leaf.value)
    if not recovered_ids:
        return False

    block.source_block_ids = list(
        dict.fromkeys([*block.source_block_ids, *recovered_ids])
    )
    _logger.info(
        "Repaired exact source citation for %s with block IDs %s",
        error.field_path,
        recovered_ids,
    )
    return True


def validate_semantic_grounding_with_exact_citation_repair(
    raw: RawExtraction,
    response: LLMSemanticCVResponse,
) -> None:
    """Validate provenance, recovering only omitted exact block citations."""
    for _ in range(32):
        try:
            validate_semantic_grounding(raw, response)
            return
        except SemanticGroundingError as error:
            if error.reason == "not_in_cited_source" and (
                _repair_missing_block_citation(raw, response, error)
                or _repair_near_verbatim_bullet(raw, response, error)
                or _repair_summary_from_cited_source(raw, response, error)
            ):
                continue
            raise
    raise SemanticGroundingError("response", "too_many_missing_citations")


def _server_block(
    block: LLMSemanticBlock,
    *,
    block_id: str,
):
    payload = block.model_dump()
    payload["block_id"] = block_id
    block_types = {
        "entry": CVEntryBlock,
        "bullet": CVBulletBlock,
        "paragraph": CVParagraphBlock,
        "skill_group": CVSkillGroupBlock,
        "publication": CVPublicationBlock,
        "education": CVEducationBlock,
        "unknown": CVUnknownBlock,
    }
    return block_types[block.type].model_validate(payload)


def assemble_semantic_document(
    *,
    raw: RawExtraction,
    response: LLMSemanticCVResponse,
    source_text: str,
    raw_extraction_ref_id: str | None,
) -> CVDocumentV2:
    """Assign server metadata and convert strict LLM candidates to CVDocumentV2."""
    validate_semantic_grounding(raw, response)
    identity_sources = response.identity.field_source_block_ids
    identity = CVIdentity(
        full_name=response.identity.full_name,
        headline=response.identity.headline,
        email=response.identity.email,
        phone=response.identity.phone,
        location=response.identity.location,
        links=response.identity.links,
        field_source_block_ids=CVIdentitySourceMap.model_validate(
            identity_sources.model_dump()
        ),
    )
    summary = None
    if response.summary:
        summary = CVParagraphBlock(
            block_id="semantic-summary",
            text=response.summary.text,
            confidence=response.summary.confidence,
            source_block_ids=response.summary.source_block_ids,
        )

    sections: list[CVSection] = []
    for section_index, candidate in enumerate(response.sections, start=1):
        section_id = f"semantic-section-{section_index}"
        blocks = [
            _server_block(
                block,
                block_id=f"{section_id}-block-{block_index}",
            )
            for block_index, block in enumerate(candidate.blocks, start=1)
        ]
        sections.append(
            CVSection(
                id=section_id,
                type=candidate.type,
                title=candidate.title,
                confidence=candidate.confidence,
                source_block_ids=candidate.source_block_ids,
                blocks=blocks,
            )
        )

    document = CVDocumentV2(
        raw_extraction_id=raw_extraction_ref_id,
        extraction_version=raw.extraction_version,
        parser_version="llm-semantic-1.0",
        requires_reprocessing=False,
        source_hash=canonical_cv_hash(source_text),
        identity=identity,
        summary=summary,
        sections=sections,
    )
    return finalize_document_provenance(
        raw,
        document,
        [
            LLMUnmappedReference.model_validate(item.model_dump())
            for item in response.unmapped_references
        ],
    )


def deterministic_structuring_fallback(
    *,
    raw: RawExtraction,
    source_text: str,
    raw_extraction_ref_id: str | None,
) -> CVDocumentV2:
    """Build an explicit stale/fallback document after parser exhaustion."""
    document = reconstruct_from_lines(raw_extraction_to_layout_lines(raw))
    document.raw_extraction_id = raw_extraction_ref_id
    document.extraction_version = raw.extraction_version
    document.parser_version = "deterministic-fallback-1.0"
    document.requires_reprocessing = True
    document.source_hash = canonical_cv_hash(source_text)
    document.reconstruction_warnings = list(
        dict.fromkeys(
            [
                *document.reconstruction_warnings,
                "semantic_parser_fallback",
            ]
        )
    )
    return finalize_document_provenance(raw, document)


def _grounding_repair_input(
    raw: RawExtraction,
    previous_response: LLMSemanticCVResponse,
    error: SemanticGroundingError,
) -> str:
    """Give the mapper exact source plus its rejected candidate for correction."""
    return (
        "AUTHORITATIVE SOURCE BLOCKS:\n"
        f"{format_raw_extraction_blocks(raw)}\n\n"
        "PREVIOUS REJECTED CANDIDATE JSON:\n"
        f"{previous_response.model_dump_json()}\n\n"
        "VALIDATION ERROR:\n"
        f"{error.field_path}: {error.reason}\n"
    )


async def structure_cv(
    *,
    cv_text: str,
    raw_extraction_ref_id: str | None = None,
    user_id: str | None = None,
    file_service: FileService | None = None,
    background_tasks: BackgroundTasks | None = None,
    on_retry: ParserRetryReporter | None = None,
) -> CVStructuringResult:
    """Resolve source authority, call the V3 range plan mapper, and assemble the document."""
    from app.services.cv_range_plan_service import structure_cv_range_plan

    try:
        range_result = await structure_cv_range_plan(
            cv_text=cv_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
            user_id=user_id,
            file_service=file_service,
            background_tasks=background_tasks,
            on_retry=on_retry,
        )
        return CVStructuringResult(
            raw_extraction=range_result.raw_extraction,
            source_text=range_result.source_text,
            document=range_result.document,
            used_fallback=range_result.used_fallback,
        )
    except Exception as exc:
        _logger.warning(
            "V3 range plan parser failed; using explicit deterministic fallback: %s: %s",
            type(exc).__name__,
            str(exc),
        )
        raw, source_text = await resolve_authoritative_source(
            cv_text=cv_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
            user_id=user_id,
            file_service=file_service,
        )
        document = deterministic_structuring_fallback(
            raw=raw,
            source_text=source_text,
            raw_extraction_ref_id=raw_extraction_ref_id,
        )
        return CVStructuringResult(raw, source_text, document, True)
