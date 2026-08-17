"""Evidence-Constrained CV Translation Service for Phase 7."""

import hashlib
import json
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.cv_document_v2 import (
    CVBulletBlock,
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVParagraphBlock,
    CVPublicationBlock,
    CVSkillGroupBlock,
    CVUnknownBlock,
)
from app.models.cv_translation import (
    CVTranslationDecision,
    CVTranslationDiagnostics,
)
from app.services.ai_service import call_llm_with_fallback
from app.services.cv_source_grounding import iter_semantic_text_leaves
from app.services.cv_translation_validation import (
    TranslationValidationError,
    validate_translation_variant,
)
from app.services.section_vocabulary import (
    SECTION_TYPE_TO_ENGLISH,
    SECTION_TYPE_TO_VIETNAMESE,
)

_logger = logging.getLogger(__name__)


def _hash_val(val: object) -> str:
    s = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class TranslationItem(BaseModel):
    field_id: str
    translated_text: str


class TranslationBatchResponse(BaseModel):
    translations: list[TranslationItem] = Field(default_factory=list)


def apply_leaf_value(doc: CVDocumentV2, field_path: str, new_value: str) -> None:
    """Mutate doc at exact canonical field_path with new_value."""
    if field_path == "summary.text" and doc.summary:
        doc.summary.text = new_value
        return

    # E.g. sections[0].title or sections[0].blocks[1].bullets[2]
    sec_match = re.match(r"^sections\[(\d+)\]\.(.+)$", field_path)
    if not sec_match:
        return
    s_idx = int(sec_match.group(1))
    sub_path = sec_match.group(2)

    if s_idx >= len(doc.sections):
        return
    sec = doc.sections[s_idx]

    if sub_path == "title":
        sec.title = new_value
        return

    blk_match = re.match(r"^blocks\[(\d+)\]\.(.+)$", sub_path)
    if not blk_match:
        return
    b_idx = int(blk_match.group(1))
    blk_path = blk_match.group(2)

    if b_idx >= len(sec.blocks):
        return
    block = sec.blocks[b_idx]

    if isinstance(block, (CVBulletBlock, CVParagraphBlock)) and blk_path == "text":
        block.text = new_value
    elif isinstance(block, CVEntryBlock):
        if blk_path == "title":
            block.title = new_value
        elif blk_path == "subtitle":
            block.subtitle = new_value
        elif blk_path == "organization":
            block.organization = new_value
        elif blk_path == "location":
            block.location = new_value
        elif blk_path == "date":
            block.date = new_value
        else:
            bullet_match = re.match(r"^bullets\[(\d+)\]$", blk_path)
            if bullet_match:
                bullet_idx = int(bullet_match.group(1))
                if bullet_idx < len(block.bullets):
                    block.bullets[bullet_idx] = new_value
    elif isinstance(block, CVEducationBlock):
        if blk_path == "institution":
            block.institution = new_value
        elif blk_path == "degree":
            block.degree = new_value
        elif blk_path == "field":
            block.field = new_value
        elif blk_path == "location":
            block.location = new_value
        elif blk_path == "date":
            block.date = new_value
        else:
            detail_match = re.match(r"^details\[(\d+)\]$", blk_path)
            if detail_match:
                d_idx = int(detail_match.group(1))
                if d_idx < len(block.details):
                    block.details[d_idx] = new_value
    elif isinstance(block, CVSkillGroupBlock):
        if blk_path == "label" and block.label is not None:
            block.label = new_value
        else:
            skill_match = re.match(r"^skills\[(\d+)\]$", blk_path)
            if skill_match:
                sk_idx = int(skill_match.group(1))
                if sk_idx < len(block.skills):
                    block.skills[sk_idx] = new_value
    elif isinstance(block, CVPublicationBlock):
        if blk_path == "title":
            block.title = new_value
        elif blk_path == "authors":
            block.authors = new_value
        elif blk_path == "venue":
            block.venue = new_value
        elif blk_path == "date":
            block.date = new_value
        elif blk_path == "status":
            block.status = new_value
    elif isinstance(block, CVUnknownBlock):
        line_match = re.match(r"^lines\[(\d+)\]$", blk_path)
        if line_match:
            l_idx = int(line_match.group(1))
            if l_idx < len(block.lines):
                block.lines[l_idx] = new_value


async def translate_cv_document(
    source_document: CVDocumentV2,
    target_language: Literal["vi", "en"],
    source_language: str = "vi",
) -> tuple[CVDocumentV2, CVTranslationDiagnostics]:
    """Translate CVDocumentV2 while guaranteeing 100% field coverage and factual conservation."""
    translated_doc = source_document.model_copy(deep=True)
    decisions: list[CVTranslationDecision] = []
    translated_count = 0
    preserved_count = 0

    # 1. Deterministic Section Localization
    for s_idx, sec in enumerate(translated_doc.sections):
        old_title = sec.title
        sec_h = _hash_val(old_title)
        if target_language == "en":
            sec.title = SECTION_TYPE_TO_ENGLISH.get(sec.type, old_title)
        elif target_language == "vi":
            sec.title = SECTION_TYPE_TO_VIETNAMESE.get(sec.type, old_title)

        new_h = _hash_val(sec.title)
        decisions.append(
            CVTranslationDecision(
                field_id=f"sections[{s_idx}].title",
                status="translated" if sec.title != old_title else "preserved",
                reason_codes=["deterministic_section_localization"],
                source_value_hash=sec_h,
                translated_value_hash=new_h,
            )
        )
        if sec.title != old_title:
            translated_count += 1
        else:
            preserved_count += 1

    # 2. Iterate ALL Leaves and classify
    translatable_items: list[dict[str, Any]] = []
    translatable_field_paths: set[str] = set()

    for leaf in iter_semantic_text_leaves(source_document):
        if (
            leaf.field_path.endswith(".title")
            and leaf.field_path.startswith("sections[")
            and ".blocks[" not in leaf.field_path
        ):
            continue  # Already handled in section localization

        val_str = leaf.value if isinstance(leaf.value, str) else " ".join(leaf.value)
        val_h = _hash_val(leaf.value)

        # Verbatim preserved fields
        if (
            leaf.field_path.startswith("identity.")
            or leaf.field_path.endswith(".organization")
            or leaf.field_path.endswith(".institution")
        ):
            decisions.append(
                CVTranslationDecision(
                    field_id=leaf.field_path,
                    status="preserved",
                    reason_codes=[
                        "identity_verbatim"
                        if leaf.field_path.startswith("identity.")
                        else "entity_verbatim"
                    ],
                    source_value_hash=val_h,
                    translated_value_hash=val_h,
                )
            )
            preserved_count += 1
        elif target_language == source_language:
            decisions.append(
                CVTranslationDecision(
                    field_id=leaf.field_path,
                    status="preserved",
                    reason_codes=["same_language_bypass"],
                    source_value_hash=val_h,
                    translated_value_hash=val_h,
                )
            )
            preserved_count += 1
        else:
            translatable_items.append({"field_id": leaf.field_path, "text": val_str})
            translatable_field_paths.add(leaf.field_path)

    # 3. LLM Translation for Translatable Items
    if translatable_items and target_language != source_language:
        system_prompt = (
            f"You are an expert professional CV translator. Translate the provided CV fields from {source_language} to {target_language}.\n"
            f"RULES:\n"
            f"1. Translate prose accurately into natural professional {target_language}.\n"
            f"2. CRITICAL: Preserve all numbers, metrics, dates, URLs, emails, technology names (FastAPI, React, etc.), and proper nouns EXACTLY as they appear.\n"
            f"3. Return a JSON object matching the requested schema with the list of translated items.\n"
        )
        user_prompt = f"Fields to translate:\n{json.dumps(translatable_items, ensure_ascii=False)}"

        try:
            llm_result: TranslationBatchResponse = await call_llm_with_fallback(
                system_prompt=system_prompt,
                user_input=user_prompt,
                response_model=TranslationBatchResponse,
                feature_name="cv_translation",
            )
        except Exception as exc:
            _logger.error("LLM translation failed: %s", exc)
            diag = CVTranslationDiagnostics(
                source_document_hash=_hash_val(source_document.model_dump(mode="json")),
                translated_document_hash="",
                source_language=source_language,
                target_language=target_language,
                is_valid=False,
            )
            raise TranslationValidationError(
                diag, f"LLM translation provider error: {exc}"
            ) from exc

        # Map translations by field_id
        translations = {
            item.field_id: item.translated_text for item in llm_result.translations
        }

        # Apply translations and record decisions
        for item in translatable_items:
            f_path = item["field_id"]
            orig_val = item["text"]
            orig_h = _hash_val(orig_val)

            new_val = translations.get(f_path, orig_val)
            apply_leaf_value(translated_doc, f_path, new_val)
            new_h = _hash_val(new_val)

            is_changed = new_val.strip() != orig_val.strip()
            decisions.append(
                CVTranslationDecision(
                    field_id=f_path,
                    status="translated" if is_changed else "preserved",
                    reason_codes=["llm_translated"]
                    if is_changed
                    else ["translation_unchanged"],
                    source_value_hash=orig_h,
                    translated_value_hash=new_h,
                )
            )
            if is_changed:
                translated_count += 1
            else:
                preserved_count += 1

    src_hash = _hash_val(source_document.model_dump(mode="json"))
    trans_hash = _hash_val(translated_doc.model_dump(mode="json"))

    diagnostics = CVTranslationDiagnostics(
        source_document_hash=src_hash,
        translated_document_hash=trans_hash,
        source_language=source_language,
        target_language=target_language,
        total_fields=len(decisions),
        translated_fields=translated_count,
        preserved_fields=preserved_count,
        decisions=decisions,
        is_valid=True,
    )

    validate_translation_variant(source_document, translated_doc, diagnostics)

    return translated_doc, diagnostics
