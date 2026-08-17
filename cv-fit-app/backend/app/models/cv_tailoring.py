"""Strict operation and response contracts for LLM #3 — CV Tailor & Enhancer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMTailoringOperation(BaseModel):
    """A bounded rewrite operation proposed by LLM #3."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(
        max_length=128,
        description="Allowed canonical-CV path, for example experience[0].bullets[1].text",
    )
    proposed_text: str = Field(min_length=1, max_length=320)
    rationale: str = Field(min_length=1, max_length=120)


class TailoringChangeItem(LLMTailoringOperation):
    """A server-validated rewrite shown to API/CLI consumers."""

    original_text: str = Field(description="Source value resolved by the server.")


class LLMTailoredCVResponse(BaseModel):
    """Small, provider-facing LLM #3 output; it must never repeat the full CV."""

    model_config = ConfigDict(extra="forbid")

    change_log: list[LLMTailoringOperation] = Field(default_factory=list, max_length=2)
    tailoring_summary: str = Field(min_length=1, max_length=500)


class TailoredCVResponse(BaseModel):
    """Server-built tailored CV returned to API/CLI consumers."""

    tailored_cv: dict[str, Any]
    change_log: list[TailoringChangeItem] = Field(default_factory=list)
    tailoring_summary: str
