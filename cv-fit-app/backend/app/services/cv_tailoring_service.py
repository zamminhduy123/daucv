"""Safe, evidence-constrained tailoring for typed CV documents (Phase 5)."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from typing import TYPE_CHECKING, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVBlockRewrite,
    CVBlockType,
    CVDocumentV2,
    CVEntryBlock,
    CVParagraphBlock,
    CVRewriteOperation,
    CVSkillGroupBlock,
    CVTailoringDiagnostics,
)

if TYPE_CHECKING:
    from app.services.cv_rewrite_service import CVRewriteEvidenceBundle

from app.services.ai_service import call_llm_with_fallback

_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?(?:\s*[%xX])?(?:[MmKkBb]\+?)?\b")
_PLACEHOLDER_RE = re.compile(r"\[.*?\]|<.*?>|\{.*?\}")

# Action verb inflation rules: weak role terms cannot be upgraded to leading role terms
_RESPONSIBILITY_INFLATION_PAIRS = [
    (
        {"assisted", "supported", "helped", "hỗ trợ", "giúp đỡ"},
        {"led", "managed", "spearheaded", "directed", "chủ trì", "dẫn dắt", "quản lý"},
    ),
    (
        {"contributed", "participated", "tham gia"},
        {"created", "architected", "founded", "thiết kế kiến trúc", "sáng lập"},
    ),
]

_BUZZWORDS = {
    "scalable",
    "high-performing",
    "increased revenue",
    "world-class",
    "spearheaded",
    "game-changing",
    "revolutionary",
    "cutting-edge",
}


def _normalize_skill_token(s: str) -> str:
    """Normalize skill strings using NFKC, whitespace stripping, and case-folding."""
    if not s:
        return ""
    normalized = unicodedata.normalize("NFKC", s).strip()
    return re.sub(r"\s+", " ", normalized).casefold()


def hash_field_value(value: str | list[str]) -> str:
    """Deterministic SHA256 hex digest of a field value."""
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFKC", value).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    sorted_items = [unicodedata.normalize("NFKC", item).strip() for item in value]
    encoded = json.dumps(sorted_items, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _numbers_in_text(text: str) -> Counter[str]:
    return Counter(match.group(0).casefold() for match in _NUMBER_RE.finditer(text))


def validate_block_rewrite_deterministic(
    bundle: CVRewriteEvidenceBundle,
    operation: CVRewriteOperation,
) -> tuple[bool, list[str]]:
    """Deterministic validation of a proposed block rewrite operation against its evidence bundle."""
    reasons: list[str] = []

    # 1. Identity & Original Value Hash Match
    if operation.original_value_hash != bundle.original_value_hash:
        reasons.append("stale_original_value_hash")
        return False, reasons

    # 2. Field Whitelist & Type Safety
    if operation.field != bundle.field:
        reasons.append("field_mismatch")
        return False, reasons

    proposed = operation.proposed_value

    if bundle.field == "text":
        if not isinstance(proposed, str):
            reasons.append("invalid_proposed_value_type_for_text")
            return False, reasons
        proposed_text = proposed
    elif bundle.field == "bullets":
        if not isinstance(proposed, list):
            reasons.append("invalid_proposed_value_type_for_bullets")
            return False, reasons
        if len(proposed) != len(bundle.original_value):
            reasons.append("bullet_count_changed")
            return False, reasons
        proposed_text = " ".join(proposed)
    elif bundle.field == "skills":
        if not isinstance(proposed, list):
            reasons.append("invalid_proposed_value_type_for_skills")
            return False, reasons
        # Multiset Counter equality
        orig_counter = Counter(_normalize_skill_token(s) for s in bundle.original_value)
        prop_counter = Counter(_normalize_skill_token(s) for s in proposed)
        if orig_counter != prop_counter:
            reasons.append("skills_added_or_removed")
            return False, reasons
        proposed_text = " ".join(proposed)
    else:
        reasons.append("field_not_mutable_for_block_type")
        return False, reasons

    if not proposed_text.strip():
        reasons.append("empty_rewrite")
        return False, reasons

    # 3. Placeholder rejection
    if _PLACEHOLDER_RE.search(proposed_text):
        reasons.append("placeholder_detected")
        return False, reasons

    # 4. Numbers & Metrics Preservation (Block-Local)
    evidence_text = "\n".join(bundle.ordered_raw_evidence)
    evidence_numbers = _numbers_in_text(evidence_text)
    proposed_numbers = _numbers_in_text(proposed_text)

    # Rejects new numbers not in local evidence
    new_numbers = proposed_numbers - evidence_numbers
    if new_numbers:
        reasons.append("unsupported_number_invented")

    # 5. Buzzword / Unsupported Impact Adjectives
    for buzz in _BUZZWORDS:
        if buzz in proposed_text.casefold() and buzz not in evidence_text.casefold():
            reasons.append(f"unsupported_buzzword:{buzz}")

    if reasons:
        return False, reasons

    return True, []


class CVRewriteSemanticVerdict(BaseModel):
    """Independent, fail-closed semantic comparison result."""

    model_config = ConfigDict(extra="forbid")

    no_new_claims: bool
    no_lost_claims: bool
    reason_codes: list[Literal["new_claim", "lost_claim", "uncertain"]] = Field(
        default_factory=list,
    )


def verify_block_rewrite_semantics(
    bundle: CVRewriteEvidenceBundle,
    operation: CVRewriteOperation,
) -> tuple[bool, list[str]]:
    """Deterministically require bidirectional block-local claim preservation."""
    orig_text = (
        bundle.original_value
        if isinstance(bundle.original_value, str)
        else " ".join(bundle.original_value)
    )
    prop_text = (
        operation.proposed_value
        if isinstance(operation.proposed_value, str)
        else " ".join(operation.proposed_value)
    )

    orig_lower = orig_text.casefold()
    prop_lower = prop_text.casefold()

    # Deterministic responsibility inflation check
    for weak_set, strong_set in _RESPONSIBILITY_INFLATION_PAIRS:
        has_weak_orig = any(w in orig_lower for w in weak_set)
        has_strong_orig = any(s in orig_lower for s in strong_set)
        has_strong_prop = any(s in prop_lower for s in strong_set)

        if has_weak_orig and not has_strong_orig and has_strong_prop:
            return False, ["responsibility_inflation_detected"]

    # This intentionally rejects uncertain paraphrases: a rewrite may reorganize
    # phrasing, but cannot add or remove material claim terms.
    original_claims = _claim_terms(orig_text)
    proposed_claims = _claim_terms(prop_text)
    if proposed_claims - original_claims:
        return False, ["semantic_new_claim_detected"]
    if original_claims - proposed_claims:
        return False, ["semantic_material_claim_removed"]

    return True, []


async def verify_block_rewrite_semantics_with_validator(
    bundle: CVRewriteEvidenceBundle,
    operation: CVRewriteOperation,
    *,
    background_tasks: object | None = None,
) -> tuple[bool, list[str]]:
    """Apply deterministic checks, then an independent fail-closed validator."""
    deterministic_valid, deterministic_reasons = verify_block_rewrite_semantics(
        bundle,
        operation,
    )
    if not deterministic_valid:
        return False, deterministic_reasons

    prompt = (
        "You are a strict block-local CV claim preservation validator. Compare only "
        "the supplied original and proposed values. Return JSON with no_new_claims, "
        "no_lost_claims, and reason_codes. A change in responsibility, object, scope, "
        "regulatory domain, metric, entity, or outcome is a new/lost claim. If uncertain, "
        "set the relevant boolean false and include uncertain. Do not improve either text."
    )
    payload = json.dumps(
        {
            "original_value": bundle.original_value,
            "proposed_value": operation.proposed_value,
            "local_evidence": bundle.ordered_raw_evidence,
        },
        ensure_ascii=False,
    )
    try:
        verdict = await call_llm_with_fallback(
            prompt,
            payload,
            CVRewriteSemanticVerdict,
            feature_name="cv_rewrite_semantic_validator",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
            max_retries=1,
        )
    except HTTPException:
        return False, ["semantic_validator_unavailable"]

    reasons: list[str] = []
    if not verdict.no_new_claims:
        reasons.append("semantic_new_claim_detected")
    if not verdict.no_lost_claims:
        reasons.append("semantic_material_claim_removed")
    reason_mapping = {
        "new_claim": "semantic_new_claim_detected",
        "lost_claim": "semantic_material_claim_removed",
        "uncertain": "semantic_validator_uncertain",
    }
    reasons.extend(reason_mapping[code] for code in verdict.reason_codes)
    return (not reasons), list(dict.fromkeys(reasons))


def validate_tailored_document_gate(
    source_document: CVDocumentV2,
    tailored_document: CVDocumentV2,
    diagnostics: CVTailoringDiagnostics,
) -> None:
    """Verify exact structure plus a one-to-one audit decision for each mutable field."""
    from app.services.tailored_cv_metadata import canonical_source_document_hash

    if diagnostics.rewrite_version != 1:
        raise ValueError("CV tailoring gate failed: unsupported rewrite version.")
    if diagnostics.source_document_hash != canonical_source_document_hash(
        source_document
    ):
        raise ValueError("CV tailoring gate failed: source document hash mismatch.")

    source_top = source_document.model_dump(exclude={"summary", "sections"})
    tailored_top = tailored_document.model_dump(exclude={"summary", "sections"})
    if source_top != tailored_top:
        raise ValueError(
            "CV tailoring gate failed: document metadata or identity changed."
        )
    if (source_document.summary is None) != (tailored_document.summary is None):
        raise ValueError("CV tailoring gate failed: summary structure changed.")
    if len(source_document.sections) != len(tailored_document.sections):
        raise ValueError("CV tailoring gate failed: section count changed.")
    for index, (source_section, tailored_section) in enumerate(
        zip(source_document.sections, tailored_document.sections, strict=True),
    ):
        if source_section.model_dump(exclude={"blocks"}) != tailored_section.model_dump(
            exclude={"blocks"}
        ):
            raise ValueError(
                f"CV tailoring gate failed: section {index} metadata changed."
            )
        if len(source_section.blocks) != len(tailored_section.blocks):
            raise ValueError(
                f"CV tailoring gate failed: section {index} block count changed."
            )

    source_blocks = _all_blocks(source_document)
    tailored_blocks = _all_blocks(tailored_document)
    if len(source_blocks) != len(tailored_blocks):
        raise ValueError("CV tailoring gate failed: block count changed.")
    source_block_ids = [block.block_id for block in source_blocks]
    tailored_block_ids = [block.block_id for block in tailored_blocks]
    if len(source_block_ids) != len(set(source_block_ids)) or len(
        tailored_block_ids
    ) != len(set(tailored_block_ids)):
        raise ValueError("CV tailoring gate failed: duplicate block identity.")

    decisions: dict[tuple[str, str], object] = {}
    operation_ids: set[str] = set()
    for decision in diagnostics.decisions:
        key = (decision.block_id, decision.field)
        if key in decisions or decision.operation_id in operation_ids:
            raise ValueError("CV tailoring gate failed: duplicate rewrite decision.")
        decisions[key] = decision
        operation_ids.add(decision.operation_id)

    mutable_keys: set[tuple[str, str]] = set()
    for source_block, tailored_block in zip(
        source_blocks, tailored_blocks, strict=True
    ):
        if (
            type(source_block) is not type(tailored_block)
            or source_block.block_id != tailored_block.block_id
        ):
            raise ValueError(
                "CV tailoring gate failed: block identity or type changed."
            )
        field = _mutable_field(source_block)
        if field is None:
            if source_block != tailored_block:
                raise ValueError("CV tailoring gate failed: immutable block changed.")
            continue

        key = (source_block.block_id, field)
        mutable_keys.add(key)
        decision = decisions.get(key)
        if decision is None:
            raise ValueError("CV tailoring gate failed: mutable field has no decision.")
        source_value = getattr(source_block, field)
        tailored_value = getattr(tailored_block, field)
        source_hash = hash_field_value(source_value)
        tailored_hash = hash_field_value(tailored_value)
        if decision.original_value_hash != source_hash:
            raise ValueError("CV tailoring gate failed: original value hash mismatch.")

        if decision.status == "accepted":
            if (
                tailored_value == source_value
                or decision.proposed_value_hash != tailored_hash
            ):
                raise ValueError(
                    "CV tailoring gate failed: accepted decision/value mismatch."
                )
            if tailored_block.origin not in {
                ContentOrigin.LLM_REWRITE,
                ContentOrigin.USER_EDIT,
            }:
                raise ValueError(
                    "CV tailoring gate failed: accepted block origin mismatch."
                )
            if (
                tailored_block.origin == ContentOrigin.USER_EDIT
                and "user_edit" not in decision.reason_codes
            ):
                raise ValueError(
                    "CV tailoring gate failed: user edit lacks an edit decision."
                )
            expected_original = {**source_block.original_values, field: source_value}
            expected_tailored = {**source_block.tailored_values, field: tailored_value}
            if (
                tailored_block.original_values != expected_original
                or tailored_block.tailored_values != expected_tailored
            ):
                raise ValueError(
                    "CV tailoring gate failed: accepted block audit values mismatch."
                )
            excluded = {field, "origin", "original_values", "tailored_values"}
            if source_block.model_dump(exclude=excluded) != tailored_block.model_dump(
                exclude=excluded
            ):
                raise ValueError(
                    "CV tailoring gate failed: accepted block immutable fields changed."
                )
        else:
            if tailored_block != source_block:
                raise ValueError(
                    "CV tailoring gate failed: non-accepted block differs from source."
                )
            if (
                decision.status == "preserved"
                and decision.proposed_value_hash != source_hash
            ):
                raise ValueError(
                    "CV tailoring gate failed: preserved decision hash mismatch."
                )
            if decision.status == "rejected" and not re.fullmatch(
                r"[0-9a-f]{64}",
                decision.proposed_value_hash,
            ):
                raise ValueError(
                    "CV tailoring gate failed: rejected decision hash is invalid."
                )

    if set(decisions) != mutable_keys:
        raise ValueError(
            "CV tailoring gate failed: decision references an unknown field."
        )
    status_counts = Counter(decision.status for decision in diagnostics.decisions)
    if (
        diagnostics.accepted_count != status_counts["accepted"]
        or diagnostics.rejected_count != status_counts["rejected"]
        or diagnostics.preserved_count != status_counts["preserved"]
    ):
        raise ValueError(
            "CV tailoring gate failed: diagnostic counts are inconsistent."
        )


def _mutable_field(block: CVBlockType) -> Literal["text", "bullets", "skills"] | None:
    if isinstance(block, CVParagraphBlock):
        return "text"
    if isinstance(block, CVEntryBlock) and block.bullets:
        return "bullets"
    if isinstance(block, CVSkillGroupBlock) and block.skills:
        return "skills"
    return None


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
_CLAIM_STOP_WORDS = {
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
    "reststructur",
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
    "phat trien",
    " xay dung",
    " quan ly",
    " dao tao",
    " huu tri",
    " nghi cu",
}


def _all_blocks(document: CVDocumentV2) -> list[CVBlockType]:
    blocks: list[CVBlockType] = []
    if document.summary is not None:
        blocks.append(document.summary)
    for section in document.sections:
        if section.type == "summary":
            continue
        blocks.extend(section.blocks)
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
