"""Compact cursor-plan contract for experimental LLM #1 v3.1.

The model receives an ordered, section-local source ledger. It only emits
semantic codes plus atom counts; the server advances the cursor and renders
all candidate text from its own source spans.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


class _StrictRangePlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SourceLedgerAtom(_StrictRangePlanModel):
    """Server-owned source fragment with offsets into its raw PDF block."""

    index: int = Field(ge=0)
    block_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    page: int = Field(ge=1)
    reading_order: int = Field(ge=0)
    bbox: tuple[float, float, float, float] | None = None
    is_bullet: bool = False
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)

    @model_validator(mode="after")
    def offsets_are_ordered(self) -> SourceLedgerAtom:
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


CursorRoleCode = Literal[
    "t",  # title / degree
    "s",  # subtitle
    "o",  # organization
    "l",  # location
    "d",  # date
    "b",  # bullet
    "x",  # standalone text
    "g",  # skill label
    "k",  # skill
    "a",  # authors
    "v",  # venue
    "q",  # publication status
    "i",  # institution
    "m",  # major/field
    "n",  # education detail
    "u",  # unclassified line
]


class CursorSegment(RootModel[tuple[CursorRoleCode, Annotated[int, Field(ge=1)]]]):
    """Compact JSON tuple: ``[role_code, atom_count]``."""

    @property
    def role(self) -> CursorRoleCode:
        return self.root[0]

    @property
    def count(self) -> int:
        return self.root[1]


CursorBlockType = Literal[
    "e",  # entry
    "b",  # standalone bullet
    "p",  # paragraph
    "s",  # skill group
    "u",  # publication
    "d",  # education
    "x",  # unknown
]

VisualHeaderRoleCode = Literal["t", "o", "l", "d", "s", "u"]


class LLMVisualEntryHeaderResponse(_StrictRangePlanModel):
    """One role label per visual-header atom, in supplied order."""

    roles: list[VisualHeaderRoleCode] = Field(
        min_length=1,
        validation_alias="r",
        serialization_alias="r",
    )


class LLMCursorPlanBlock(_StrictRangePlanModel):
    """Compact semantic block: kind plus ordered cursor segments."""

    kind: CursorBlockType = Field(validation_alias="k", serialization_alias="k")
    segments: list[CursorSegment] = Field(
        min_length=1,
        validation_alias="s",
        serialization_alias="s",
    )


class LLMSectionCursorPlanResponse(_StrictRangePlanModel):
    """Section response. No text, source IDs, offsets, or coverage echo."""

    blocks: list[LLMCursorPlanBlock] = Field(
        default_factory=list,
        validation_alias="b",
        serialization_alias="b",
    )
