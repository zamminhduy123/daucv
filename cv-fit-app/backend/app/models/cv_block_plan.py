"""LLM #1 v2 source-atom plan models.

The mapper is intentionally unable to author CV text.  It can only classify
and group IDs emitted by the server-owned source atomizer.  The companion
adapter reconstructs every visible string from those atoms.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.cv_document_v2 import CVSectionType


class _StrictPlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _unique_ids(ids: list[str], *, field_name: str = "atom_ids") -> list[str]:
    if len(ids) != len(set(ids)):
        raise ValueError(f"{field_name} must be unique")
    return ids


class SourceAtom(_StrictPlanModel):
    """One server-owned, displayable fragment of one raw source block."""

    atom_id: str
    block_id: str
    text: str = Field(min_length=1)
    page: int = Field(ge=1)
    reading_order: int = Field(ge=0)
    ordinal: int = Field(ge=0)


class AtomIdentityPlan(_StrictPlanModel):
    full_name_atom_ids: list[str] = Field(default_factory=list)
    headline_atom_ids: list[str] = Field(default_factory=list)
    email_atom_ids: list[str] = Field(default_factory=list)
    phone_atom_ids: list[str] = Field(default_factory=list)
    location_atom_ids: list[str] = Field(default_factory=list)
    link_atom_id_groups: list[list[str]] = Field(default_factory=list)

    @field_validator(
        "full_name_atom_ids",
        "headline_atom_ids",
        "email_atom_ids",
        "phone_atom_ids",
        "location_atom_ids",
    )
    @classmethod
    def unique_scalar_ids(cls, value: list[str]) -> list[str]:
        return _unique_ids(value)

    @field_validator("link_atom_id_groups")
    @classmethod
    def unique_link_ids(cls, value: list[list[str]]) -> list[list[str]]:
        return [_unique_ids(group) for group in value]

    def referenced_atom_ids(self) -> list[str]:
        ids = [
            *self.full_name_atom_ids,
            *self.headline_atom_ids,
            *self.email_atom_ids,
            *self.phone_atom_ids,
            *self.location_atom_ids,
        ]
        for group in self.link_atom_id_groups:
            ids.extend(group)
        return ids


class _AtomBlockPlan(_StrictPlanModel):
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    def referenced_atom_ids(self) -> list[str]:
        raise NotImplementedError


class AtomEntryPlan(_AtomBlockPlan):
    type: Literal["entry"]
    title_atom_ids: list[str] = Field(min_length=1)
    subtitle_atom_ids: list[str] = Field(default_factory=list)
    organization_atom_ids: list[str] = Field(default_factory=list)
    location_atom_ids: list[str] = Field(default_factory=list)
    date_atom_ids: list[str] = Field(default_factory=list)
    bullet_atom_id_groups: list[list[str]] = Field(default_factory=list)

    def referenced_atom_ids(self) -> list[str]:
        return [
            *self.title_atom_ids,
            *self.subtitle_atom_ids,
            *self.organization_atom_ids,
            *self.location_atom_ids,
            *self.date_atom_ids,
            *(atom_id for group in self.bullet_atom_id_groups for atom_id in group),
        ]


class AtomBulletPlan(_AtomBlockPlan):
    type: Literal["bullet"]
    text_atom_ids: list[str] = Field(min_length=1)

    def referenced_atom_ids(self) -> list[str]:
        return self.text_atom_ids


class AtomParagraphPlan(_AtomBlockPlan):
    type: Literal["paragraph"]
    text_atom_ids: list[str] = Field(min_length=1)

    def referenced_atom_ids(self) -> list[str]:
        return self.text_atom_ids


class AtomSkillGroupPlan(_AtomBlockPlan):
    type: Literal["skill_group"]
    label_atom_ids: list[str] = Field(default_factory=list)
    skill_atom_id_groups: list[list[str]] = Field(default_factory=list)

    def referenced_atom_ids(self) -> list[str]:
        return [
            *self.label_atom_ids,
            *(atom_id for group in self.skill_atom_id_groups for atom_id in group),
        ]


class AtomPublicationPlan(_AtomBlockPlan):
    type: Literal["publication"]
    title_atom_ids: list[str] = Field(min_length=1)
    authors_atom_ids: list[str] = Field(default_factory=list)
    venue_atom_ids: list[str] = Field(default_factory=list)
    date_atom_ids: list[str] = Field(default_factory=list)
    status_atom_ids: list[str] = Field(default_factory=list)

    def referenced_atom_ids(self) -> list[str]:
        return [
            *self.title_atom_ids,
            *self.authors_atom_ids,
            *self.venue_atom_ids,
            *self.date_atom_ids,
            *self.status_atom_ids,
        ]


class AtomEducationPlan(_AtomBlockPlan):
    type: Literal["education"]
    institution_atom_ids: list[str] = Field(default_factory=list)
    degree_atom_ids: list[str] = Field(default_factory=list)
    field_atom_ids: list[str] = Field(default_factory=list)
    location_atom_ids: list[str] = Field(default_factory=list)
    date_atom_ids: list[str] = Field(default_factory=list)
    detail_atom_id_groups: list[list[str]] = Field(default_factory=list)

    def referenced_atom_ids(self) -> list[str]:
        return [
            *self.institution_atom_ids,
            *self.degree_atom_ids,
            *self.field_atom_ids,
            *self.location_atom_ids,
            *self.date_atom_ids,
            *(atom_id for group in self.detail_atom_id_groups for atom_id in group),
        ]


class AtomUnknownPlan(_AtomBlockPlan):
    type: Literal["unknown"]
    line_atom_ids: list[str] = Field(min_length=1)

    def referenced_atom_ids(self) -> list[str]:
        return self.line_atom_ids


LLMAtomBlockPlan = Annotated[
    AtomEntryPlan
    | AtomBulletPlan
    | AtomParagraphPlan
    | AtomSkillGroupPlan
    | AtomPublicationPlan
    | AtomEducationPlan
    | AtomUnknownPlan,
    Field(discriminator="type"),
]


class AtomSectionPlan(_StrictPlanModel):
    type: CVSectionType
    title_atom_ids: list[str] = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    blocks: list[LLMAtomBlockPlan] = Field(default_factory=list)

    def referenced_atom_ids(self) -> list[str]:
        return [
            *self.title_atom_ids,
            *(
                atom_id
                for block in self.blocks
                for atom_id in block.referenced_atom_ids()
            ),
        ]


class LLMAtomPlanResponse(_StrictPlanModel):
    """V2 LLM response: semantic plan only; never user-visible CV text."""

    identity: AtomIdentityPlan = Field(default_factory=AtomIdentityPlan)
    summary_atom_ids: list[str] = Field(default_factory=list)
    sections: list[AtomSectionPlan] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    def referenced_atom_ids(self) -> set[str]:
        return {
            *self.identity.referenced_atom_ids(),
            *self.summary_atom_ids,
            *(
                atom_id
                for section in self.sections
                for atom_id in section.referenced_atom_ids()
            ),
        }


class LLMSectionAtomPlanResponse(_StrictPlanModel):
    """Small, section-local plan returned by one staged mapper request."""

    # This mandatory echo makes the model explicitly account for every input
    # atom before it emits semantic groupings. It is audit-only and never
    # becomes a visible CV field.
    coverage_atom_ids: list[str] = Field(default_factory=list)
    blocks: list[LLMAtomBlockPlan] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    def referenced_atom_ids(self) -> set[str]:
        return {
            atom_id for block in self.blocks for atom_id in block.referenced_atom_ids()
        }
