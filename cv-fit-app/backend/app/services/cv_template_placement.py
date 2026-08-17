"""Template placement manifest for Phase 6 template layouts."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.cv_document_v2 import CVDocumentV2, CVSection, CVSectionType
from app.models.cv_template import CVTemplateDefinition

SlotType = Literal["header", "sidebar", "main"]


class SectionPlacement(BaseModel):
    """Placement mapping for a single section into a layout slot."""

    section_id: str
    section_type: CVSectionType
    target_slot: SlotType


class CVTemplatePlacementManifest(BaseModel):
    """Template-specific placement manifest separating semantics from layout."""

    template_id: str
    layout: Literal["single_column", "sidebar"]
    placements: list[SectionPlacement] = Field(default_factory=list)

    def get_slot_for_section(self, section: CVSection) -> SlotType:
        if self.layout == "single_column":
            return "main"

        # Sidebar layout placement based strictly on section.type
        if section.type in ("skills", "education"):
            return "sidebar"

        # Experience, Summary, Projects, Custom, and Unknown sections render in main
        return "main"


def build_placement_manifest(
    document: CVDocumentV2,
    template_def: CVTemplateDefinition,
) -> CVTemplatePlacementManifest:
    """Build structural placement manifest for document sections in target template."""
    manifest = CVTemplatePlacementManifest(
        template_id=template_def.template_id,
        layout=template_def.layout,
    )
    for idx, section in enumerate(document.sections):
        sec_id = section.id if section.id else f"sec_{idx}"
        slot = manifest.get_slot_for_section(section)
        manifest.placements.append(
            SectionPlacement(
                section_id=sec_id,
                section_type=section.type,
                target_slot=slot,
            )
        )
    return manifest
