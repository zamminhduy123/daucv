"""Strict LLM-only schema for semantic CV structuring.

These models intentionally exclude server-owned document IDs, source text,
geometry, extraction/version fields, and persisted unmapped content.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.cv_document_v2 import CVSectionType


class _StrictLLMModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _unique_source_ids(ids: list[str]) -> list[str]:
    if len(ids) != len(set(ids)):
        raise ValueError("source_block_ids must be unique")
    return ids


class LLMIdentitySourceMap(_StrictLLMModel):
    full_name: list[str] = Field(default_factory=list)
    headline: list[str] = Field(default_factory=list)
    email: list[str] = Field(default_factory=list)
    phone: list[str] = Field(default_factory=list)
    location: list[str] = Field(default_factory=list)
    links: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("full_name", "headline", "email", "phone", "location")
    @classmethod
    def unique_scalar_source_ids(cls, value: list[str]) -> list[str]:
        return _unique_source_ids(value)

    @field_validator("links")
    @classmethod
    def unique_link_source_ids(
        cls,
        value: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        return {link: _unique_source_ids(ids) for link, ids in value.items()}

    def all_source_block_ids(self) -> list[str]:
        ids = [
            *self.full_name,
            *self.headline,
            *self.email,
            *self.phone,
            *self.location,
        ]
        for link_ids in self.links.values():
            ids.extend(link_ids)
        return list(dict.fromkeys(ids))


class LLMIdentityCandidate(_StrictLLMModel):
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    field_source_block_ids: LLMIdentitySourceMap = Field(
        default_factory=LLMIdentitySourceMap,
    )

    @model_validator(mode="after")
    def require_provenance_for_present_fields(self) -> "LLMIdentityCandidate":
        for field_name in ("full_name", "headline", "email", "phone", "location"):
            if getattr(self, field_name) and not getattr(
                self.field_source_block_ids,
                field_name,
            ):
                raise ValueError(f"{field_name} requires source_block_ids")
        # Link citations are repaired against the authoritative raw blocks in
        # ``cv_structuring_service``. Keep this parsing model permissive so an
        # omitted link map does not discard an otherwise complete LLM response
        # before that exact-match repair can run.
        return self


class LLMBlockBase(_StrictLLMModel):
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_block_ids: list[str] = Field(min_length=1)

    @field_validator("source_block_ids")
    @classmethod
    def unique_block_sources(cls, value: list[str]) -> list[str]:
        return _unique_source_ids(value)


class LLMEntryBlock(LLMBlockBase):
    type: Literal["entry"]
    title: str
    subtitle: str | None = None
    organization: str | None = None
    location: str | None = None
    date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class LLMBulletBlock(LLMBlockBase):
    type: Literal["bullet"]
    text: str


class LLMParagraphBlock(LLMBlockBase):
    type: Literal["paragraph"]
    text: str


class LLMSkillGroupBlock(LLMBlockBase):
    type: Literal["skill_group"]
    label: str | None = None
    skills: list[str] = Field(default_factory=list)


class LLMPublicationBlock(LLMBlockBase):
    type: Literal["publication"]
    title: str
    authors: str | None = None
    venue: str | None = None
    date: str | None = None
    status: str | None = None


class LLMEducationBlock(LLMBlockBase):
    type: Literal["education"]
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    date: str | None = None
    details: list[str] = Field(default_factory=list)


class LLMUnknownBlock(LLMBlockBase):
    type: Literal["unknown"]
    lines: list[str] = Field(default_factory=list)


LLMSemanticBlock = Annotated[
    LLMEntryBlock
    | LLMBulletBlock
    | LLMParagraphBlock
    | LLMSkillGroupBlock
    | LLMPublicationBlock
    | LLMEducationBlock
    | LLMUnknownBlock,
    Field(discriminator="type"),
]


class LLMSummaryCandidate(LLMBlockBase):
    text: str


class LLMSectionCandidate(_StrictLLMModel):
    type: CVSectionType
    title: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_block_ids: list[str] = Field(min_length=1)
    blocks: list[LLMSemanticBlock] = Field(default_factory=list)

    @field_validator("source_block_ids")
    @classmethod
    def unique_section_sources(cls, value: list[str]) -> list[str]:
        return _unique_source_ids(value)


class LLMUnmappedCandidate(_StrictLLMModel):
    block_id: str
    reason: Literal[
        "unknown_section",
        "decorative_content",
        "placeholder_content",
        "ambiguous_content",
    ]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class LLMSemanticCVResponse(_StrictLLMModel):
    """Semantic-only response returned by the parser LLM."""

    identity: LLMIdentityCandidate = Field(default_factory=LLMIdentityCandidate)
    summary: LLMSummaryCandidate | None = None
    sections: list[LLMSectionCandidate] = Field(default_factory=list)
    unmapped_references: list[LLMUnmappedCandidate] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def unique_unmapped_ids(self) -> "LLMSemanticCVResponse":
        ids = [item.block_id for item in self.unmapped_references]
        if len(ids) != len(set(ids)):
            raise ValueError("unmapped block IDs must be unique")
        return self

    def mapped_source_block_ids(self) -> set[str]:
        ids = set(self.identity.field_source_block_ids.all_source_block_ids())
        if self.summary:
            ids.update(self.summary.source_block_ids)
        for section in self.sections:
            ids.update(section.source_block_ids)
            for block in section.blocks:
                ids.update(block.source_block_ids)
        return ids

    def referenced_source_block_ids(self) -> set[str]:
        return self.mapped_source_block_ids() | {
            item.block_id for item in self.unmapped_references
        }
