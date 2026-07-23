"""Safe, block-ID based tailoring for typed CV documents."""

from __future__ import annotations

import json
import re
from collections import Counter

from app.models.cv_document_v2 import (
    CVBlockRewrite,
    CVBlockType,
    CVDocumentV2,
    CVEntryBlock,
    CVParagraphBlock,
    CVSkillGroupBlock,
)

_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?(?:\s*[%xX])?(?:[MmKkBb]\+?)?\b")
_KNOWN_TECHNOLOGIES = {
    "airflow",
    "angular",
    "aws",
    "azure",
    "c#",
    "c++",
    "django",
    "docker",
    "elasticsearch",
    "fastapi",
    "flask",
    "gcp",
    "graphql",
    "java",
    "javascript",
    "kafka",
    "kotlin",
    "kubernetes",
    "mongodb",
    "mysql",
    "next.js",
    "node.js",
    "postgresql",
    "pytorch",
    "python",
    "react",
    "redis",
    "rust",
    "spark",
    "spring",
    "sql",
    "swift",
    "tensorflow",
    "terraform",
    "typescript",
    "vue",
}
_SAFE_REWRITE_WORDS = {"clear", "clearly", "using"}

# Words excluded from factual-claim detection.
# Common CV action verbs and paraphrase synonyms are safe to swap — they
# do not add factual information about the candidate.
#
# Includes both full words and aggressively-stemmed forms (the
# _claim_root function strips up to the final character of 5+ letter
# words, so "developed"→"devel", "implemented"→"implement", etc.).
_CLAIM_STOP_WORDS = {
    # Articles & prepositions
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "va",
    "và",
    "cho",
    "cua",
    "của",
    "trong",
    "voi",
    "với",
    # Common CV action verbs (full and aggressively-stemmed forms)
    "build",
    "built",
    "buil",
    "develop",
    "devel",
    "create",
    "crea",
    "designed",
    "design",
    "designe",
    "implement",
    "implemente",
    "implem",
    "write",
    "writ",
    "engineer",
    "deliver",
    "deliv",
    "manage",
    "manag",
    "lead",
    "direct",
    "oversee",
    "overs",
    "support",
    "assist",
    "assists",
    "improv",
    "optimiz",
    "enhanc",
    "strengthen",
    "strength",
    "drive",
    "driv",
    "spearhead",
    "spearhe",
    "coordinate",
    "coordinat",
    "collaborate",
    "collaborat",
    "partner",
    "partners",
    "mentor",
    "guide",
    "guides",
    "train",
    "trains",
    "teach",
    "teaches",
    "research",
    "analy",
    "investigat",
    "study",
    "studies",
    "evaluate",
    "evalu",
    "assess",
    "review",
    "reviews",
    "architect",
    "architec",
    "construct",
    "establish",
    "launch",
    "deploy",
    "rollout",
    "rollouts",
    "migrat",
    "refactor",
    "refactors",
    "restructure",
    "restructur",
    "streamlin",
    "automate",
    "automat",
    "integrate",
    "integr",
    "configure",
    "configur",
    "maintain",
    "maintains",
    "operat",
    "administer",
    "monitor",
    "monitors",
    "debug",
    "debugs",
    "troubleshoot",
    "troubleshoots",
    "resolve",
    "resolv",
    "fix",
    "fixes",
    "patch",
    "patches",
    "test",
    "tests",
    "validate",
    "validat",
    "verify",
    "verifies",
    "certify",
    "certifi",
    "communicate",
    "communicat",
    "present",
    "presents",
    "report",
    "reports",
    "document",
    "documents",
    "author",
    "authors",
    "compose",
    "compos",
    "draft",
    "negotiate",
    "negotiat",
    "persuade",
    "persuades",
    "influence",
    "influenc",
    "convince",
    "convinces",
    "facilitate",
    "facilitat",
    "mediate",
    "mediates",
    "sell",
    "sells",
    "market",
    "markets",
    "promote",
    "promotes",
    "advertise",
    "brand",
    "brands",
    "merchandis",
    "hire",
    "hires",
    "recruit",
    "recruits",
    "select",
    "selects",
    "screen",
    "screens",
    "interview",
    "interviews",
    "onboard",
    "onboards",
    "retain",
    "retains",
    "plan",
    "plans",
    "schedule",
    "schedules",
    "organize",
    "organizes",
    "prioriti",
    "allocat",
    "assign",
    "assigns",
    "delegate",
    "delegates",
    "execute",
    "executes",
    "perform",
    "performs",
    "complete",
    "complet",
    "accomplish",
    "achieve",
    "achieves",
    "attain",
    "attains",
    "reach",
    "reaches",
    "produce",
    "produces",
    "generate",
    "generates",
    "output",
    "outputs",
    "manufacture",
    "manufactur",
    "fabricate",
    "fabricat",
    "assemble",
    "assembles",
    "collect",
    "collects",
    "gather",
    "gathers",
    "aggregate",
    "aggregates",
    "compile",
    "compiles",
    "consolidate",
    "consolidat",
    "synthesiz",
    "formulat",
    "devis",
    "conceiv",
    "invent",
    "invents",
    "innovate",
    "innovates",
    "pioneer",
    "pioneers",
    "originate",
    "originates",
    # Vietnamese common verbs
    "phat trien",
    " xay dung",
    " quan ly",
    " dao tao",
    " huu tri",
    " nghi cu",
}


def rewrite_payload(document: CVDocumentV2) -> str:
    """Return the only mutable fields the LLM is allowed to propose."""
    payload = {
        "schema_version": document.schema_version,
        "blocks": [_rewrite_input(block) for block in _all_blocks(document)],
    }
    return json.dumps(payload, ensure_ascii=False)


def apply_block_rewrites(
    document: CVDocumentV2,
    rewrites: list[CVBlockRewrite],
    source_text: str,
) -> tuple[CVDocumentV2, list[str]]:
    """Validate and apply rewrites independently, restoring rejected blocks."""
    result = document.model_copy(deep=True)
    blocks = {block.block_id: block for block in _all_blocks(result)}
    warnings: list[str] = []
    counts = Counter(rewrite.block_id for rewrite in rewrites)

    for block_id, count in counts.items():
        if count > 1:
            warnings.append(f"rewrite_rejected:{block_id}:duplicate_block_id")

    supplied_ids = set(counts)
    expected_ids = set(blocks)
    for block_id in sorted(expected_ids - supplied_ids):
        warnings.append(f"rewrite_missing:{block_id}")
    for block_id in sorted(supplied_ids - expected_ids):
        warnings.append(f"rewrite_rejected:{block_id}:unknown_block_id")

    source_numbers = _numbers(source_text)
    source_technologies = _technologies(source_text)
    source_named_entities = _proper_names(source_text)
    source_claim_terms = _claim_terms(source_text)
    for rewrite in rewrites:
        block = blocks.get(rewrite.block_id)
        if block is None or counts[rewrite.block_id] > 1:
            continue
        rejection = _validate_rewrite(
            block,
            rewrite,
            source_numbers=source_numbers,
            source_technologies=source_technologies,
            source_named_entities=source_named_entities,
            source_claim_terms=source_claim_terms,
        )
        if rejection:
            warnings.append(f"rewrite_rejected:{rewrite.block_id}:{rejection}")
            continue
        _apply_rewrite(block, rewrite)

    result.reconstruction_warnings = list(
        dict.fromkeys([*result.reconstruction_warnings, *warnings]),
    )
    return result, warnings


def _all_blocks(document: CVDocumentV2) -> list[CVBlockType]:
    blocks: list[CVBlockType] = []
    if document.summary is not None:
        blocks.append(document.summary)
    blocks.extend(block for section in document.sections for block in section.blocks)
    return blocks


def _rewrite_input(block: CVBlockType) -> dict[str, object]:
    payload: dict[str, object] = {"block_id": block.block_id, "type": block.type}
    if isinstance(block, CVParagraphBlock):
        payload["original_text"] = block.text
    elif isinstance(block, CVEntryBlock):
        payload["original_bullets"] = block.bullets
    elif isinstance(block, CVSkillGroupBlock):
        payload["original_skills"] = block.skills
    return payload


def _validate_rewrite(
    block: CVBlockType,
    rewrite: CVBlockRewrite,
    *,
    source_numbers: set[str],
    source_technologies: set[str],
    source_named_entities: set[str],
    source_claim_terms: set[str],
) -> str | None:
    proposed_fields = sum(
        value is not None for value in (rewrite.text, rewrite.bullets, rewrite.skills)
    )
    if rewrite.preserve:
        return None if proposed_fields == 0 else "preserve_with_mutation"
    if proposed_fields != 1:
        return "exactly_one_mutation_required"

    candidate_text = ""
    if isinstance(block, CVParagraphBlock) and rewrite.text is not None:
        candidate_text = rewrite.text
    elif isinstance(block, CVEntryBlock) and rewrite.bullets is not None:
        if len(rewrite.bullets) != len(block.bullets):
            return "bullet_count_changed"
        candidate_text = " ".join(rewrite.bullets)
    elif isinstance(block, CVSkillGroupBlock) and rewrite.skills is not None:
        if Counter(item.casefold() for item in rewrite.skills) != Counter(
            item.casefold() for item in block.skills
        ):
            return "skills_added_or_removed"
        candidate_text = " ".join(rewrite.skills)
    else:
        return "field_not_mutable_for_block_type"

    if not candidate_text.strip():
        return "empty_rewrite"
    if _numbers(candidate_text) - source_numbers:
        return "unsupported_number"
    if _technologies(candidate_text) - source_technologies:
        return "unsupported_technology"
    if _proper_names(candidate_text) - source_named_entities:
        return "unsupported_named_entity"
    unsupported_claim_terms = _claim_terms(candidate_text) - source_claim_terms
    if unsupported_claim_terms:
        return "unsupported_claim_terms"
    return None


def _apply_rewrite(block: CVBlockType, rewrite: CVBlockRewrite) -> None:
    if isinstance(block, CVParagraphBlock) and rewrite.text is not None:
        block.original_values["text"] = block.text
        block.tailored_values["text"] = rewrite.text
        block.text = rewrite.text
    elif isinstance(block, CVEntryBlock) and rewrite.bullets is not None:
        block.original_values["bullets"] = list(block.bullets)
        block.tailored_values["bullets"] = list(rewrite.bullets)
        block.bullets = list(rewrite.bullets)
    elif isinstance(block, CVSkillGroupBlock) and rewrite.skills is not None:
        block.original_values["skills"] = list(block.skills)
        block.tailored_values["skills"] = list(rewrite.skills)
        block.skills = list(rewrite.skills)


def _numbers(text: str) -> set[str]:
    return {match.group(0).casefold() for match in _NUMBER_RE.finditer(text)}


def _technologies(text: str) -> set[str]:
    lower = text.casefold()
    return {technology for technology in _KNOWN_TECHNOLOGIES if technology in lower}


def _proper_names(text: str) -> set[str]:
    """Conservatively identify capitalized named tokens away from sentence starts."""
    names: set[str] = set()
    for match in re.finditer(r"\b[^\W\d_][^\W\d_.+#-]{2,}\b", text):
        token = match.group(0)
        if not token[0].isupper():
            continue
        prefix = text[: match.start()].rstrip()
        if not prefix or prefix.endswith((".", "!", "?", "\n")):
            continue
        normalized = token.casefold()
        if normalized not in _KNOWN_TECHNOLOGIES:
            names.add(normalized)
    return names


def _claim_terms(text: str) -> set[str]:
    terms = {
        _claim_root(token)
        for token in re.findall(r"[^\W\d_]{2,}", text, flags=re.UNICODE)
    }
    return {
        term
        for term in terms
        if term not in _CLAIM_STOP_WORDS and term not in _SAFE_REWRITE_WORDS
    }


def _claim_root(token: str) -> str:
    """Normalize simple English inflections without allowlisting factual claims."""
    term = token.casefold()
    if len(term) > 5 and term.endswith("ing"):
        term = term[:-3]
        if len(term) > 2 and term[-1] == term[-2]:
            term = term[:-1]
    elif (len(term) > 4 and term.endswith("ied")) or (
        len(term) > 4 and term.endswith("ies")
    ):
        term = f"{term[:-3]}y"
    elif len(term) > 4 and term.endswith("ed"):
        term = term[:-2]
    elif len(term) > 4 and term.endswith("s"):
        term = term[:-1]
    return term[:-1] if len(term) > 4 and term.endswith("e") else term


def validate_tailored_document(
    source_document: CVDocumentV2,
    candidate_document: CVDocumentV2,
    source_text: str,
) -> tuple[CVDocumentV2, list[str]]:
    """Revalidate a client-supplied tailored document against server source."""
    structural_warnings: list[str] = []
    if candidate_document.identity != source_document.identity:
        structural_warnings.append("rewrite_structure_rejected:identity_changed")
    if len(candidate_document.sections) != len(source_document.sections):
        structural_warnings.append("rewrite_structure_rejected:section_count_changed")

    source_sections = [
        (section.type, section.title, [block.block_id for block in section.blocks])
        for section in source_document.sections
    ]
    candidate_sections = [
        (section.type, section.title, [block.block_id for block in section.blocks])
        for section in candidate_document.sections
    ]
    if candidate_sections != source_sections:
        structural_warnings.append(
            "rewrite_structure_rejected:section_structure_changed"
        )

    source_blocks = {block.block_id: block for block in _all_blocks(source_document)}
    candidate_blocks = {
        block.block_id: block for block in _all_blocks(candidate_document)
    }
    rewrites: list[CVBlockRewrite] = []
    for block_id, source_block in source_blocks.items():
        candidate = candidate_blocks.get(block_id)
        if candidate is None or type(candidate) is not type(source_block):
            rewrites.append(CVBlockRewrite(block_id=block_id, preserve=True))
            continue
        if _immutable_values(candidate) != _immutable_values(source_block):
            structural_warnings.append(
                f"rewrite_rejected:{block_id}:immutable_fields_changed",
            )
            rewrites.append(CVBlockRewrite(block_id=block_id, preserve=True))
        elif isinstance(source_block, CVParagraphBlock):
            rewrites.append(
                CVBlockRewrite(block_id=block_id, text=candidate.text)
                if candidate.text != source_block.text
                else CVBlockRewrite(block_id=block_id, preserve=True),
            )
        elif isinstance(source_block, CVEntryBlock):
            rewrites.append(
                CVBlockRewrite(block_id=block_id, bullets=candidate.bullets)
                if candidate.bullets != source_block.bullets
                else CVBlockRewrite(block_id=block_id, preserve=True),
            )
        elif isinstance(source_block, CVSkillGroupBlock):
            rewrites.append(
                CVBlockRewrite(block_id=block_id, skills=candidate.skills)
                if candidate.skills != source_block.skills
                else CVBlockRewrite(block_id=block_id, preserve=True),
            )
        else:
            rewrites.append(CVBlockRewrite(block_id=block_id, preserve=True))

    validated, rewrite_warnings = apply_block_rewrites(
        source_document,
        rewrites,
        source_text,
    )
    warnings = list(dict.fromkeys([*structural_warnings, *rewrite_warnings]))
    validated.reconstruction_warnings = list(
        dict.fromkeys([*validated.reconstruction_warnings, *warnings]),
    )
    return validated, warnings


def _immutable_values(block: CVBlockType) -> dict[str, object]:
    excluded = {
        "block_id",
        "confidence",
        "source_line_ids",
        "reconstruction_warnings",
        "original_values",
        "tailored_values",
        "text",
        "bullets",
        "skills",
    }
    return block.model_dump(exclude=excluded)
