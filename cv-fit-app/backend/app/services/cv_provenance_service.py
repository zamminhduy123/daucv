import re
from dataclasses import dataclass

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVReconstructionDiagnostics,
    CVSourceCoverageDiagnostics,
    CVSourceCoverageIssue,
    CVUnmappedContent,
    LLMUnmappedReference,
    deterministic_unmapped_fragment_id,
)
from app.models.cv_raw_extraction import RawExtraction
from app.services.cv_source_grounding import (
    collect_all_source_block_ids,
    iter_semantic_text_leaves,
    match_leaf_to_source,
    normalize_source,
)


@dataclass(frozen=True)
class SourceConservationResult:
    document: CVDocumentV2
    diagnostics: CVSourceCoverageDiagnostics
    is_valid: bool
    rejection_reasons: list[str]


def _is_hierarchical_parent(path_a: str, path_b: str) -> bool:
    """Check if path_a is a hierarchical parent of path_b or vice versa."""
    if path_a == path_b:
        return True

    if path_a.startswith(path_b) and (
        len(path_a) == len(path_b) or path_a[len(path_b)] in {".", "["}
    ):
        return True
    if path_b.startswith(path_a) and (
        len(path_b) == len(path_a) or path_b[len(path_a)] in {".", "["}
    ):
        return True

    # Check identity hierarchy (e.g. "identity" and "identity.full_name")
    if path_a == "identity" and path_b.startswith("identity."):
        return True
    return path_b == "identity" and path_a.startswith("identity.")


def _get_alnum_count(text: str) -> int:
    return len(re.findall(r"\w", text))


def audit_source_conservation(
    raw: RawExtraction,
    document: CVDocumentV2,
    llm_unmapped: list[LLMUnmappedReference] | None = None,
) -> SourceConservationResult:
    llm_unmapped = llm_unmapped or []
    issues: list[CVSourceCoverageIssue] = []
    rejection_reasons: list[str] = []

    valid_block_ids = {block.block_id for page in raw.pages for block in page.blocks}
    referenced_ids = collect_all_source_block_ids(document)
    llm_unmapped_ids = {u.block_id for u in llm_unmapped}

    for unknown_id in (referenced_ids | llm_unmapped_ids) - valid_block_ids:
        issues.append(
            CVSourceCoverageIssue(code="unknown_source_reference", block_id=unknown_id)
        )
        rejection_reasons.append(f"unknown_source_reference: block_id={unknown_id}")

    source = normalize_source(raw)

    consumed_spans: dict[str, list[tuple[int, int, str]]] = {
        b: [] for b in valid_block_ids
    }

    # Match every semantic text leaf
    for leaf in iter_semantic_text_leaves(document):
        if not leaf.value or not leaf.value.strip():
            continue

        used_spans = {
            b: [(s[0], s[1]) for s in spans] for b, spans in consumed_spans.items()
        }
        matches = match_leaf_to_source(leaf, source, used_spans=used_spans)

        if not matches:
            # Unmatched non-empty leaf -> grounding failure
            block_id = leaf.source_block_ids[0] if leaf.source_block_ids else "unknown"
            issues.append(
                CVSourceCoverageIssue(
                    code="unmatched_semantic_leaf",
                    block_id=block_id,
                    field_paths=[leaf.field_path],
                    significant_character_count=_get_alnum_count(leaf.value),
                )
            )
            rejection_reasons.append(
                f"unmatched_semantic_leaf: field={leaf.field_path}, block_id={block_id}"
            )
            continue

        for match in matches:
            if match.block_id not in consumed_spans:
                continue

            new_start, new_end = match.start, match.end

            for existing_start, existing_end, existing_path in consumed_spans[
                match.block_id
            ]:
                overlap_start = max(new_start, existing_start)
                overlap_end = min(new_end, existing_end)
                if overlap_start < overlap_end and not _is_hierarchical_parent(
                    leaf.field_path, existing_path
                ):
                    issues.append(
                        CVSourceCoverageIssue(
                            code="duplicate_semantic_ownership",
                            block_id=match.block_id,
                            field_paths=[leaf.field_path, existing_path],
                        )
                    )
                    rejection_reasons.append(
                        f"duplicate_semantic_ownership: block_id={match.block_id}, fields={leaf.field_path},{existing_path}"
                    )

            consumed_spans[match.block_id].append((new_start, new_end, leaf.field_path))

    significant_character_count = 0
    mapped_significant_chars = 0
    benign_unmapped_character_count = 0
    substantive_unmapped_character_count = 0
    duplicate_character_count = 0

    accounted_block_count = 0
    generated_unmapped: list[CVUnmappedContent] = []

    for page in raw.pages:
        for block in page.blocks:
            block_id = block.block_id
            original_text = block.text
            norm_block = source.block_map.get(block_id)
            if not norm_block:
                continue

            significant_character_count += _get_alnum_count(original_text)

            spans = consumed_spans.get(block_id, [])
            if spans or block_id in llm_unmapped_ids:
                accounted_block_count += 1

            sorted_spans = sorted(spans, key=lambda x: (x[0], x[1]))
            merged_spans: list[tuple[int, int]] = []
            for s in sorted_spans:
                if not merged_spans:
                    merged_spans.append((s[0], s[1]))
                else:
                    last = merged_spans[-1]
                    if s[0] <= last[1]:
                        overlap = min(last[1], s[1]) - s[0]
                        if overlap > 0:
                            duplicate_character_count += overlap
                        merged_spans[-1] = (last[0], max(last[1], s[1]))
                    else:
                        merged_spans.append((s[0], s[1]))

            for ms in merged_spans:
                span_text = norm_block.normalized_text[ms[0] : ms[1]]
                mapped_significant_chars += _get_alnum_count(span_text)

            residuals: list[tuple[int, int, str]] = []
            curr = 0
            for ms in merged_spans:
                if ms[0] > curr:
                    residuals.append(
                        (curr, ms[0], norm_block.normalized_text[curr : ms[0]])
                    )
                curr = ms[1]
            if curr < len(norm_block.normalized_text):
                residuals.append(
                    (
                        curr,
                        len(norm_block.normalized_text),
                        norm_block.normalized_text[curr:],
                    )
                )

            block_has_substantive = False
            substantive_chars_in_block = 0

            for r_start, r_end, r_text in residuals:
                if any(character.isalnum() for character in r_text):
                    substantive_len = len(r_text)
                    substantive_unmapped_character_count += substantive_len
                    block_has_substantive = True
                    substantive_chars_in_block += substantive_len

                    # Exact original offsets via norm_to_orig_map
                    if norm_block.norm_to_orig_map and r_start < len(
                        norm_block.norm_to_orig_map
                    ):
                        source_start = norm_block.norm_to_orig_map[r_start][0]
                        map_end_idx = min(
                            r_end - 1, len(norm_block.norm_to_orig_map) - 1
                        )
                        source_end = norm_block.norm_to_orig_map[map_end_idx][1]
                        orig_frag = original_text[source_start:source_end]
                    else:
                        source_start = 0
                        source_end = len(original_text)
                        orig_frag = original_text

                    frag_id = deterministic_unmapped_fragment_id(
                        block_id,
                        source_start,
                        source_end,
                    )

                    generated_unmapped.append(
                        CVUnmappedContent(
                            block_id=block_id,
                            text=orig_frag,
                            page=block.page,
                            reason="parser_omission",
                            confidence=None,
                            fragment_id=frag_id,
                            source_start=source_start,
                            source_end=source_end,
                        )
                    )
                else:
                    benign_unmapped_character_count += len(r_text)

            # Strict server-side omission check: any substantive unmapped text fails conservation.
            # LLM decorative/placeholder tags cannot bypass substantive content omission.
            if block_has_substantive:
                issues.append(
                    CVSourceCoverageIssue(
                        code="substantive_source_omission",
                        block_id=block_id,
                        significant_character_count=substantive_chars_in_block,
                    )
                )
                rejection_reasons.append(
                    f"substantive_source_omission: block_id={block_id}, {substantive_chars_in_block} significant chars uncovered"
                )

    coverage_ratio = (
        min(1.0, mapped_significant_chars / significant_character_count)
        if significant_character_count > 0
        else 1.0
    )

    diagnostics = CVSourceCoverageDiagnostics(
        raw_block_count=len(valid_block_ids),
        accounted_block_count=accounted_block_count,
        significant_character_count=significant_character_count,
        mapped_character_count=mapped_significant_chars,
        benign_unmapped_character_count=benign_unmapped_character_count,
        substantive_unmapped_character_count=substantive_unmapped_character_count,
        duplicate_character_count=duplicate_character_count,
        coverage_ratio=coverage_ratio,
        issues=issues,
    )

    is_valid = not document.requires_reprocessing and not any(
        i.code
        in {
            "substantive_source_omission",
            "duplicate_semantic_ownership",
            "ambiguous_source_match",
            "unknown_source_reference",
            "unmatched_semantic_leaf",
        }
        for i in issues
    )

    existing_unmapped_keys = {(u.block_id, u.text) for u in document.unmapped_content}
    for g in generated_unmapped:
        if (g.block_id, g.text) not in existing_unmapped_keys:
            document.unmapped_content.append(g)
            existing_unmapped_keys.add((g.block_id, g.text))

    # Attach source_coverage to document's reconstruction diagnostics
    if document.reconstruction_diagnostics:
        document.reconstruction_diagnostics.source_coverage = diagnostics
    else:
        document.reconstruction_diagnostics = CVReconstructionDiagnostics(
            reconstruction_version=4,
            source_coverage=diagnostics,
        )

    return SourceConservationResult(
        document=document,
        diagnostics=diagnostics,
        is_valid=is_valid,
        rejection_reasons=rejection_reasons,
    )
