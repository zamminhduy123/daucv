"""Canonical semantic render ledger for Phase 6 template rendering.

Generates a template-independent ledger of every displayable field in CVDocumentV2.
"""

import hashlib

from pydantic import BaseModel, Field

from app.models.cv_document_v2 import (
    CVBlockType,
    CVBulletBlock,
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVParagraphBlock,
    CVPublicationBlock,
    CVSkillGroupBlock,
    CVUnknownBlock,
)


class LedgerItem(BaseModel):
    """Template-independent record for a single displayable CV field."""

    field_id: str
    expected_text: str
    expected_count: int = 1


class CVRenderLedger(BaseModel):
    """Complete semantic field ledger for a CVDocumentV2 instance."""

    document_hash: str
    items: dict[str, LedgerItem] = Field(default_factory=dict)

    def add_item(self, field_id: str, text: str, expected_count: int = 1) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        if field_id in self.items:
            # Duplicate ID detection
            self.items[field_id].expected_count += expected_count
        else:
            self.items[field_id] = LedgerItem(
                field_id=field_id,
                expected_text=clean_text,
                expected_count=expected_count,
            )


def build_cv_render_ledger(document: CVDocumentV2) -> CVRenderLedger:
    """Build canonical render ledger for document content conservation."""
    doc_json = document.model_dump_json()
    doc_hash = hashlib.sha256(doc_json.encode("utf-8")).hexdigest()
    ledger = CVRenderLedger(document_hash=doc_hash)

    # 1. Identity
    if document.identity.full_name:
        ledger.add_item("identity:full_name", document.identity.full_name)
    if document.identity.headline:
        ledger.add_item("identity:headline", document.identity.headline)

    # 2. Contacts — Single projection (canonical fields preferred, fallback to contact_lines)
    canonical_contacts = document.identity.canonical_contact_lines()
    contact_source = (
        canonical_contacts if canonical_contacts else document.identity.contact_lines
    )
    for idx, contact_line in enumerate(contact_source):
        ledger.add_item(f"contact:line:{idx}", contact_line)

    # 3. Summary
    if document.summary and document.summary.text:
        ledger.add_item("summary:text", document.summary.text)

    # 4. Sections & Blocks
    for sec_idx, section in enumerate(document.sections):
        if section.type == "custom" and "unclassified" in (section.title or "").lower():
            continue
        sec_key = f"section:{section.id if section.id else sec_idx}"
        if section.title:
            ledger.add_item(f"{sec_key}:title", section.title)

        if section.type == "summary":
            # Summary text is rendered once via document.summary ("summary:text"), not per-block
            continue

        for block_idx, block in enumerate(section.blocks):
            block_key = f"{sec_key}:block:{block_idx}"
            _populate_block_ledger(ledger, block_key, block)

    return ledger


def _populate_block_ledger(
    ledger: CVRenderLedger, block_key: str, block: CVBlockType
) -> None:
    if isinstance(block, CVEntryBlock):
        if block.title:
            ledger.add_item(f"{block_key}:title", block.title)
        if block.subtitle:
            ledger.add_item(f"{block_key}:subtitle", block.subtitle)
        if block.organization:
            ledger.add_item(f"{block_key}:organization", block.organization)
        if block.location:
            ledger.add_item(f"{block_key}:location", block.location)
        if block.date:
            ledger.add_item(f"{block_key}:date", block.date)
        for bullet_idx, bullet in enumerate(block.bullets):
            ledger.add_item(f"{block_key}:bullet:{bullet_idx}", bullet)

    elif isinstance(block, (CVBulletBlock, CVParagraphBlock)):
        if block.text:
            ledger.add_item(f"{block_key}:text", block.text)

    elif isinstance(block, CVSkillGroupBlock):
        if block.label:
            ledger.add_item(f"{block_key}:label", block.label)
        for skill_idx, skill in enumerate(block.skills):
            ledger.add_item(f"{block_key}:skill:{skill_idx}", skill)

    elif isinstance(block, CVPublicationBlock):
        if block.title:
            ledger.add_item(f"{block_key}:title", block.title)
        if block.authors:
            ledger.add_item(f"{block_key}:authors", block.authors)
        if block.venue:
            ledger.add_item(f"{block_key}:venue", block.venue)
        if block.date:
            ledger.add_item(f"{block_key}:date", block.date)
        if block.status:
            ledger.add_item(f"{block_key}:status", block.status)

    elif isinstance(block, CVEducationBlock):
        if block.institution:
            ledger.add_item(f"{block_key}:institution", block.institution)
        if block.degree:
            ledger.add_item(f"{block_key}:degree", block.degree)
        if block.field:
            ledger.add_item(f"{block_key}:field", block.field)
        if block.location:
            ledger.add_item(f"{block_key}:location", block.location)
        if block.date:
            ledger.add_item(f"{block_key}:date", block.date)
        for detail_idx, detail in enumerate(block.details):
            ledger.add_item(f"{block_key}:detail:{detail_idx}", detail)

    elif isinstance(block, CVUnknownBlock):
        for line_idx, line in enumerate(block.lines):
            ledger.add_item(f"{block_key}:line:{line_idx}", line)
