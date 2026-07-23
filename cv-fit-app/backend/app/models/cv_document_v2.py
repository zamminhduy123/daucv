"""CVDocumentV2 — Typed CV document model.

Replaces the legacy string-array sections (TailoredCV.sections: {title, items[]})
with a discriminated-union block model that preserves semantic meaning:
  entry blocks  — job / project records with title, subtitle, bullets
  bullet blocks  — loose bullet points inside a section
  paragraph blocks — plain text (summary, descriptions)
  skill_group blocks — labeled skill categories
  publication blocks — academic citations with authors, title, venue, date
  education blocks — degree / institution / date records
  unknown blocks — content the parser could not confidently classify

Every block carries a stable `block_id` so that LLM rewriting and validation
can track which content survived, changed, or was rejected.
"""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Section type
# ---------------------------------------------------------------------------

CVSectionType = Literal[
    "summary",
    "experience",
    "projects",
    "skills",
    "education",
    "publications",
    "certifications",
    "languages",
    "awards",
    "activities",
    "interests",
    "custom",
]


# ---------------------------------------------------------------------------
# Typed blocks (discriminated union via `type` tag)
# ---------------------------------------------------------------------------


class CVBlockBase(BaseModel):
    """Metadata shared by every reconstructed block."""

    block_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source_line_ids: list[str] = Field(default_factory=list)
    reconstruction_warnings: list[str] = Field(default_factory=list)
    original_values: dict[str, str | list[str]] = Field(default_factory=dict)
    tailored_values: dict[str, str | list[str]] = Field(default_factory=dict)


class CVEntryBlock(CVBlockBase):
    """A record with a title line (bold) and optional subtitle/date/organization."""

    type: Literal["entry"] = "entry"
    title: str
    subtitle: str | None = None
    organization: str | None = None
    location: str | None = None
    date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class CVBulletBlock(CVBlockBase):
    """A standalone bullet point (not attached to an entry)."""

    type: Literal["bullet"] = "bullet"
    text: str


class CVParagraphBlock(CVBlockBase):
    """Plain text — no semantic structure beyond a single string."""

    type: Literal["paragraph"] = "paragraph"
    text: str


class CVSkillGroupBlock(CVBlockBase):
    """A labeled group of related skills (e.g. 'AI/ML Research: PyTorch, ...')."""

    type: Literal["skill_group"] = "skill_group"
    label: str | None = None
    skills: list[str] = Field(default_factory=list)


class CVPublicationBlock(CVBlockBase):
    """An academic publication / citation."""

    type: Literal["publication"] = "publication"
    title: str
    authors: str | None = None
    venue: str | None = None
    date: str | None = None
    status: str | None = None


class CVEducationBlock(CVBlockBase):
    """An education record (institution, degree, date, etc.)."""

    type: Literal["education"] = "education"
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    date: str | None = None
    details: list[str] = Field(default_factory=list)


class CVUnknownBlock(CVBlockBase):
    """Content the parser could not confidently classify."""

    type: Literal["unknown"] = "unknown"
    lines: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


# ---------------------------------------------------------------------------
# Union type
# ---------------------------------------------------------------------------

CVBlockType = (
    CVEntryBlock
    | CVBulletBlock
    | CVParagraphBlock
    | CVSkillGroupBlock
    | CVPublicationBlock
    | CVEducationBlock
    | CVUnknownBlock
)

# Backward-compatible alias
CVBlock = CVBlockType


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------


class CVSection(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    type: CVSectionType
    title: str
    blocks: list[CVBlockType] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Identity block
# ---------------------------------------------------------------------------


class CVIdentity(BaseModel):
    """Candidate identity extracted from the top of the CV."""

    name: str = ""
    headline: str = ""
    contact_lines: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Document V2
# ---------------------------------------------------------------------------


class CVDocumentV2(BaseModel):
    schema_version: Literal[2] = 2
    reconstruction_version: int = 2
    source_hash: str | None = None
    identity: CVIdentity = Field(default_factory=CVIdentity)
    summary: CVParagraphBlock | None = Field(default=None)
    sections: list[CVSection] = Field(default_factory=list)
    reconstruction_warnings: list[str] = Field(default_factory=list)


class CVReconstructionDiagnostics(BaseModel):
    """Diagnostics returned separately from the user-facing analysis."""

    reconstruction_version: int = 2
    warnings: list[str] = Field(default_factory=list)
    block_confidence: dict[str, float] = Field(default_factory=dict)


class CVBlockRewrite(BaseModel):
    """Strict block-ID rewrite candidate returned by the LLM."""

    block_id: str
    text: str | None = None
    bullets: list[str] | None = None
    skills: list[str] | None = None
    preserve: bool = False
