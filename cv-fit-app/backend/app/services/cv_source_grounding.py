import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_raw_extraction import RawExtraction

_LEADING_BULLET_RE = re.compile(
    r"(?m)^[\t ]*(?:[•◦▪‣⁃●○■□◆◇►▸→*](?:[\t ]+|(?=\S))|[-–—][\t ]+)"
)
_LAYOUT_SEPARATOR_RE = re.compile(r"[\t ]*[|¦·][\t ]*")


@dataclass
class NormalizedSourceBlock:
    block_id: str
    page: int
    reading_order: int
    page_index: int
    block_index: int
    original_text: str
    normalized_text: str
    norm_to_orig_map: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class NormalizedSource:
    blocks: list[NormalizedSourceBlock]
    block_map: dict[str, NormalizedSourceBlock]


@dataclass
class SemanticTextLeaf:
    field_path: str
    value: str
    normalized_value: str
    source_block_ids: list[str]
    semantic_owner: str


@dataclass
class SourceSpanMatch:
    block_id: str
    start: int
    end: int
    leaf: SemanticTextLeaf


def normalize_grounding_text(text: str) -> str:
    """Normalize layout artifacts without changing case, words, or punctuation."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    normalized = _LEADING_BULLET_RE.sub("", normalized)
    normalized = _LAYOUT_SEPARATOR_RE.sub(" ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def build_norm_to_orig_map(
    original_text: str, normalized_text: str
) -> list[tuple[int, int]]:
    """Build a mapping from each character index in normalized_text to (start, end) in original_text.

    Uses monotonic prefix alignment: for each character position `i` in normalized_text,
    we find the character range in original_text corresponding to the expansion of normalized_text[:i+1].
    """
    if not normalized_text or not original_text:
        return []

    orig_len = len(original_text)
    norm_len = len(normalized_text)
    index_map: list[tuple[int, int]] = []

    prefix_orig_ends: list[int] = [0] * (norm_len + 1)
    orig_k = 0

    for norm_i in range(1, norm_len + 1):
        while orig_k < orig_len:
            norm_sub = normalize_grounding_text(original_text[:orig_k])
            if len(norm_sub) >= norm_i or norm_sub == normalized_text:
                while orig_k < orig_len and unicodedata.category(
                    original_text[orig_k]
                ).startswith("M"):
                    orig_k += 1
                break
            orig_k += 1
        prefix_orig_ends[norm_i] = max(orig_k, prefix_orig_ends[norm_i - 1])

    prefix_orig_ends[norm_len] = orig_len

    for i in range(norm_len):
        start = prefix_orig_ends[i]
        end = prefix_orig_ends[i + 1]
        if end <= start:
            end = min(start + 1, orig_len)
        index_map.append((start, end))

    return index_map


def normalize_source(raw: RawExtraction) -> NormalizedSource:
    blocks: list[NormalizedSourceBlock] = []
    block_map: dict[str, NormalizedSourceBlock] = {}
    for page_index, page in enumerate(raw.pages):
        for block_index, raw_block in enumerate(page.blocks):
            norm_text = normalize_grounding_text(raw_block.text)
            norm_map = build_norm_to_orig_map(raw_block.text, norm_text)
            norm_block = NormalizedSourceBlock(
                block_id=raw_block.block_id,
                page=page.page,
                reading_order=raw_block.reading_order,
                page_index=page_index,
                block_index=block_index,
                original_text=raw_block.text,
                normalized_text=norm_text,
                norm_to_orig_map=norm_map,
            )
            blocks.append(norm_block)
            block_map[raw_block.block_id] = norm_block
    blocks.sort(
        key=lambda block: (
            block.page,
            block.reading_order,
            block.page_index,
            block.block_index,
        )
    )
    return NormalizedSource(blocks=blocks, block_map=block_map)


def collect_all_source_block_ids(document: CVDocumentV2) -> set[str]:
    """Collect all source block IDs and legacy line IDs referenced across the document."""
    ids: set[str] = set()

    if document.identity:
        ids.update(document.identity.source_block_ids)
        fm = document.identity.field_source_block_ids
        for field_ids in (fm.full_name, fm.headline, fm.email, fm.phone, fm.location):
            ids.update(field_ids)
        for link_ids in fm.links.values():
            ids.update(link_ids)

    if document.summary:
        ids.update(document.summary.source_block_ids)
        legacy_summary_ids = getattr(document.summary, "source_line_ids", [])
        if legacy_summary_ids:
            ids.update(legacy_summary_ids)

    for section in document.sections:
        ids.update(section.source_block_ids)
        for block in section.blocks:
            ids.update(block.source_block_ids)
            legacy_line_ids = getattr(block, "source_line_ids", [])
            if legacy_line_ids:
                ids.update(legacy_line_ids)

    return ids


def iter_semantic_text_leaves(document: CVDocumentV2) -> Iterable[SemanticTextLeaf]:
    identity = document.identity
    identity_sources = identity.field_source_block_ids

    for field_name in ("full_name", "headline", "email", "phone", "location"):
        val = getattr(identity, field_name)
        if val is not None:
            source_ids = (
                getattr(identity_sources, field_name) or identity.source_block_ids
            )
            yield SemanticTextLeaf(
                field_path=f"identity.{field_name}",
                value=val,
                normalized_value=normalize_grounding_text(val),
                source_block_ids=source_ids,
                semantic_owner="identity",
            )

    for link_index, link in enumerate(identity.links):
        # LLM-only identity candidates do not have the server-owned aggregate
        # ``source_block_ids`` field. An empty list deliberately lets semantic
        # grounding report the missing citation for exact repair.
        source_ids = identity_sources.links.get(link) or getattr(
            identity,
            "source_block_ids",
            [],
        )
        yield SemanticTextLeaf(
            field_path=f"identity.links[{link_index}]",
            value=link,
            normalized_value=normalize_grounding_text(link),
            source_block_ids=source_ids,
            semantic_owner="identity",
        )

    if document.summary and document.summary.text:
        yield SemanticTextLeaf(
            field_path="summary.text",
            value=document.summary.text,
            normalized_value=normalize_grounding_text(document.summary.text),
            source_block_ids=document.summary.source_block_ids,
            semantic_owner="summary",
        )

    for section_index, section in enumerate(document.sections):
        section_path = f"sections[{section_index}]"

        yield SemanticTextLeaf(
            field_path=f"{section_path}.title",
            value=section.title,
            normalized_value=normalize_grounding_text(section.title),
            source_block_ids=section.source_block_ids,
            semantic_owner="section_title",
        )

        if section.type == "summary":
            continue

        for block_index, block in enumerate(section.blocks):
            block_path = f"{section_path}.blocks[{block_index}]"
            source_ids = block.source_block_ids

            if block.type == "entry":
                for field_name in (
                    "title",
                    "subtitle",
                    "organization",
                    "location",
                    "date",
                ):
                    val = getattr(block, field_name)
                    if val is not None:
                        yield SemanticTextLeaf(
                            field_path=f"{block_path}.{field_name}",
                            value=val,
                            normalized_value=normalize_grounding_text(val),
                            source_block_ids=source_ids,
                            semantic_owner=block.type,
                        )
                for bullet_index, bullet in enumerate(block.bullets):
                    if bullet is not None:
                        yield SemanticTextLeaf(
                            field_path=f"{block_path}.bullets[{bullet_index}]",
                            value=bullet,
                            normalized_value=normalize_grounding_text(bullet),
                            source_block_ids=source_ids,
                            semantic_owner=block.type,
                        )
            elif block.type in {"bullet", "paragraph"}:
                val = block.text
                if val is not None:
                    yield SemanticTextLeaf(
                        field_path=f"{block_path}.text",
                        value=val,
                        normalized_value=normalize_grounding_text(val),
                        source_block_ids=source_ids,
                        semantic_owner=block.type,
                    )
            elif block.type == "skill_group":
                if block.label is not None:
                    yield SemanticTextLeaf(
                        field_path=f"{block_path}.label",
                        value=block.label,
                        normalized_value=normalize_grounding_text(block.label),
                        source_block_ids=source_ids,
                        semantic_owner=block.type,
                    )
                for skill_index, skill in enumerate(block.skills):
                    if skill is not None:
                        yield SemanticTextLeaf(
                            field_path=f"{block_path}.skills[{skill_index}]",
                            value=skill,
                            normalized_value=normalize_grounding_text(skill),
                            source_block_ids=source_ids,
                            semantic_owner=block.type,
                        )
            elif block.type == "publication":
                for field_name in (
                    "title",
                    "authors",
                    "venue",
                    "date",
                    "status",
                ):
                    val = getattr(block, field_name)
                    if val is not None:
                        yield SemanticTextLeaf(
                            field_path=f"{block_path}.{field_name}",
                            value=val,
                            normalized_value=normalize_grounding_text(val),
                            source_block_ids=source_ids,
                            semantic_owner=block.type,
                        )
            elif block.type == "education":
                for field_name in (
                    "institution",
                    "degree",
                    "field",
                    "location",
                    "date",
                ):
                    val = getattr(block, field_name)
                    if val is not None:
                        yield SemanticTextLeaf(
                            field_path=f"{block_path}.{field_name}",
                            value=val,
                            normalized_value=normalize_grounding_text(val),
                            source_block_ids=source_ids,
                            semantic_owner=block.type,
                        )
                for detail_index, detail in enumerate(block.details):
                    if detail is not None:
                        yield SemanticTextLeaf(
                            field_path=f"{block_path}.details[{detail_index}]",
                            value=detail,
                            normalized_value=normalize_grounding_text(detail),
                            source_block_ids=source_ids,
                            semantic_owner=block.type,
                        )
            elif block.type == "unknown":
                for line_index, line in enumerate(block.lines):
                    if line is not None:
                        yield SemanticTextLeaf(
                            field_path=f"{block_path}.lines[{line_index}]",
                            value=line,
                            normalized_value=normalize_grounding_text(line),
                            source_block_ids=source_ids,
                            semantic_owner=block.type,
                        )


def match_leaf_to_source(
    leaf: SemanticTextLeaf,
    source: NormalizedSource,
    used_spans: dict[str, list[tuple[int, int]]] | None = None,
) -> list[SourceSpanMatch]:
    matches: list[SourceSpanMatch] = []
    if not leaf.normalized_value:
        return matches

    leaf_norm = leaf.normalized_value

    def _overlaps(block_id: str, start: int, end: int) -> bool:
        if not used_spans or block_id not in used_spans:
            return False
        for u_start, u_end in used_spans[block_id]:
            if max(start, u_start) < min(end, u_end):
                return True
        return False

    # 1. Direct contiguous matching within each cited block
    for block_id in leaf.source_block_ids:
        source_block = source.block_map.get(block_id)
        if not source_block or not source_block.normalized_text:
            continue

        search_pos = 0
        block_text = source_block.normalized_text

        while search_pos < len(block_text):
            found_start = block_text.find(leaf_norm, search_pos)
            if found_start == -1:
                break
            found_end = found_start + len(leaf_norm)

            if not _overlaps(block_id, found_start, found_end):
                matches.append(
                    SourceSpanMatch(
                        block_id=block_id,
                        start=found_start,
                        end=found_end,
                        leaf=leaf,
                    )
                )
                break  # Found non-overlapping occurrence in this block

            search_pos = found_start + 1

    if matches:
        return matches

    # 2. Exact Ordered Multi-Block Matching: if leaf value spans across cited blocks
    if len(leaf.source_block_ids) > 1:
        composite_norm = ""
        composite_char_map: list[tuple[str, int, int]] = []
        cited_block_ids = set(leaf.source_block_ids)

        for source_block in source.blocks:
            if (
                source_block.block_id not in cited_block_ids
                or not source_block.normalized_text
            ):
                continue

            if composite_norm:
                composite_norm += " "
                composite_char_map.append(
                    (source_block.block_id, 0, 0)
                )  # boundary separator space

            block_text = source_block.normalized_text
            for c_i in range(len(block_text)):
                composite_char_map.append((source_block.block_id, c_i, c_i + 1))
            composite_norm += block_text

        if composite_norm:
            search_pos = 0
            while search_pos < len(composite_norm):
                c_start = composite_norm.find(leaf_norm, search_pos)
                if c_start == -1:
                    break
                c_end = c_start + len(leaf_norm)
                block_spans: dict[str, tuple[int, int]] = {}

                for idx in range(c_start, c_end):
                    if idx < len(composite_char_map):
                        bid, b_s, b_e = composite_char_map[idx]
                        if b_s < b_e:
                            if bid not in block_spans:
                                block_spans[bid] = (b_s, b_e)
                            else:
                                block_spans[bid] = (
                                    block_spans[bid][0],
                                    max(block_spans[bid][1], b_e),
                                )

                valid_multi_match = True
                proposed_matches: list[SourceSpanMatch] = []
                for bid, (b_s, b_e) in block_spans.items():
                    if _overlaps(bid, b_s, b_e):
                        valid_multi_match = False
                        break
                    proposed_matches.append(
                        SourceSpanMatch(
                            block_id=bid,
                            start=b_s,
                            end=b_e,
                            leaf=leaf,
                        )
                    )

                if valid_multi_match and proposed_matches:
                    matches.extend(proposed_matches)
                    break

                search_pos = c_start + 1

    return matches
