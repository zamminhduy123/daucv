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

Every block carries stable `source_block_ids` so that LLM rewriting and validation
can track which content survived, changed, or was rejected.
"""

import re
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.models.cv_raw_extraction import RawExtraction


class ContentOrigin(str, Enum):
    EXTRACTED = "extracted"
    LLM_REWRITE = "llm_rewrite"
    USER_EDIT = "user_edit"


class CVTextValue(BaseModel):
    """Field-level string value with provenance tracking."""

    value: str
    source_block_ids: list[str] = Field(default_factory=list)
    origin: ContentOrigin = ContentOrigin.EXTRACTED


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
    source_block_ids: list[str] = Field(default_factory=list)
    source_line_ids: list[str] = Field(default_factory=list)
    origin: ContentOrigin = ContentOrigin.EXTRACTED
    reconstruction_warnings: list[str] = Field(default_factory=list)
    original_values: dict[str, str | list[str]] = Field(default_factory=dict)
    tailored_values: dict[str, str | list[str]] = Field(default_factory=dict)
    hidden: bool = Field(
        default=False,
        description="User-set in the review wizard: hide this brick on export/preview without deleting it.",
    )


_JOB_TITLE_KEYWORDS = re.compile(
    r"\b(?:engineer|developer|scientist|assistant|manager|lead|intern|designer|"
    r"analyst|specialist|consultant|officer|fellow|postdoc|phd|m\.s\.|b\.sc\.|"
    r"director|architect|founder|builder|researcher|lecturer|professor)\b",
    re.IGNORECASE,
)
_GEOGRAPHIC_TOKEN_RE = re.compile(
    r"\b(?:city|district|province|state|vietnam|korea|japan|singapore|"
    r"usa|united states|canada|australia|remote|hybrid|on-site)\b",
    re.IGNORECASE,
)


_EMPTY_PARENS_RE = re.compile(r"\(\s*\)|（\s*）|\[\s*\]|\{\s*\}")
_DANGLING_SEPARATORS_RE = re.compile(r"^[\s|•·–—/,-]+|[\s|•·–—/,-]+$")


def _sanitize_entry_text(text: Any) -> str | None:
    """Clean empty parentheses, dangling separators, and normalize whitespace."""
    if not isinstance(text, str):
        return None
    val = _EMPTY_PARENS_RE.sub("", text)
    prev = None
    while prev != val:
        prev = val
        val = _DANGLING_SEPARATORS_RE.sub("", val).strip()
        val = _EMPTY_PARENS_RE.sub("", val)
    return val if val else None


class CVEntryBlock(CVBlockBase):
    """A record with a title line (bold) and optional subtitle/date/organization."""

    type: Literal["entry"] = "entry"
    title: str
    subtitle: str | None = None
    organization: str | None = None
    location: str | None = None
    date: str | None = None
    bullets: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sanitize_entry_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for field in ("title", "subtitle", "organization", "location", "date"):
            if field in cleaned and cleaned[field] is not None:
                sanitized = _sanitize_entry_text(cleaned[field])
                if field == "title":
                    cleaned[field] = sanitized or ""
                else:
                    cleaned[field] = sanitized
        return cleaned

    @model_validator(mode="after")
    def sanitize_location_title_swap(self) -> "CVEntryBlock":
        """Prevent geographic location strings from occupying the title field."""
        if not self.title:
            return self

        title_clean = self.title.strip()
        # If title contains clear job title keywords, it is definitely a valid title, not a location
        if _JOB_TITLE_KEYWORDS.search(title_clean):
            return self

        # If location is already populated and title does not match geographic tokens, do not swap
        if self.location and not _GEOGRAPHIC_TOKEN_RE.search(title_clean):
            return self

        is_location_pattern = bool(
            re.match(
                r"^(?:[A-Za-z\s.-]+,\s*[A-Za-z\s.-]+|Remote|Hybrid|On-site)$",
                title_clean,
                re.IGNORECASE,
            )
        ) and bool(_GEOGRAPHIC_TOKEN_RE.search(title_clean))

        if is_location_pattern:
            if not self.location:
                self.location = title_clean
            if self.subtitle:
                self.title = self.subtitle
                self.subtitle = None
            elif self.organization:
                parts = re.split(r"\s*(?:\||•|·|–|-)\s*", self.organization)
                if len(parts) >= 2:
                    self.organization = parts[0].strip()
                    self.title = parts[1].strip()
                else:
                    self.title = self.organization
                    self.organization = None
        return self


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

    @model_validator(mode="before")
    @classmethod
    def sanitize_publication_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for field in ("title", "authors", "venue", "date", "status"):
            if field in cleaned and cleaned[field] is not None:
                sanitized = _sanitize_entry_text(cleaned[field])
                if field == "title":
                    cleaned[field] = sanitized or ""
                else:
                    cleaned[field] = sanitized
        return cleaned


class CVEducationBlock(CVBlockBase):
    """An education record (institution, degree, date, etc.)."""

    type: Literal["education"] = "education"
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    date: str | None = None
    details: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sanitize_education_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for field in ("institution", "degree", "field", "location", "date"):
            if field in cleaned and cleaned[field] is not None:
                cleaned[field] = _sanitize_entry_text(cleaned[field])
        return cleaned


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
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source_block_ids: list[str] = Field(default_factory=list)
    blocks: list[CVBlockType] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Identity block
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
_LINK_PATTERN = re.compile(
    r"(?:https?://|www\.)[^\s|•,;]+|(?:linkedin|github)\.com/[^\s|•,;]+",
    re.IGNORECASE,
)
_GOOGLE_TRACKING_PARAM_RE = re.compile(
    r"[?&](?:sa|ust|usg|source|ved|opi|sntz)=[^&#\s]*",
    re.IGNORECASE,
)
_GOOGLE_REDIRECT_URL_RE = re.compile(
    r"https?://(?:[a-zA-Z0-9.-]+\.)?google\.[a-z.]+/url\?[^\s)\]>]+",
    re.IGNORECASE,
)
_NON_NAME_CHARS_RE = re.compile(r"[@<>{}[\]\\/~_+=^%$#*0-9]")


def unwrap_google_redirect_url(url: str) -> str:
    """Unwrap google.com/url?q=<real> redirects and discard Google tracking params."""
    if not isinstance(url, str) or not url:
        return url
    if "google." not in url or "/url" not in url:
        return url
    try:
        to_parse = url if "://" in url else f"https://{url}"
        parsed = urlparse(to_parse)
        netloc_parts = parsed.netloc.lower().split(":")
        domain = netloc_parts[0]
        if (
            domain == "google.com"
            or domain.endswith(".google.com")
            or ".google." in domain
        ) and parsed.path.rstrip("/") == "/url":
            qs = parse_qs(parsed.query, keep_blank_values=False)
            targets = qs.get("q") or qs.get("url")
            if targets and targets[0]:
                clean_target = _GOOGLE_TRACKING_PARAM_RE.sub("", targets[0]).rstrip(
                    "?&"
                )
                return clean_target
    except Exception:
        pass
    return url


def unwrap_google_urls_in_text(text: str) -> str:
    """Find and unwrap all google redirect URLs within free text."""
    if (
        not isinstance(text, str)
        or not text
        or "google." not in text
        or "/url" not in text
    ):
        return text

    def _replace_match(m: re.Match[str]) -> str:
        raw_match = m.group(0)
        trailing_punct = ""
        while raw_match and raw_match[-1] in ".,;:)]>\"'":
            trailing_punct = raw_match[-1] + trailing_punct
            raw_match = raw_match[:-1]
        unwrapped = unwrap_google_redirect_url(raw_match)
        return unwrapped + trailing_punct

    return _GOOGLE_REDIRECT_URL_RE.sub(_replace_match, text)


def _looks_like_person_name(text: str) -> bool:
    """Check if text is shaped like a human person's name.

    Prefers 2-5 word Title Case or UPPERCASE strings (Unicode-aware).
    Rejects emails, URLs, phones, job titles, headings, and locations.
    """
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    if _NON_NAME_CHARS_RE.search(stripped):
        return False
    if (
        _EMAIL_PATTERN.search(stripped)
        or _LINK_PATTERN.search(stripped)
        or _PHONE_PATTERN.search(stripped)
    ):
        return False
    if _JOB_TITLE_KEYWORDS.search(stripped):
        return False
    if _GEOGRAPHIC_TOKEN_RE.search(stripped):
        return False

    words = stripped.split()
    if len(words) < 1 or len(words) > 5:
        return False
    if not any(len(w) >= 2 for w in words):
        return False

    cased_words = sum(1 for w in words if w.istitle() or w.isupper())
    if len(words) == 1:
        return cased_words == 1 and len(words[0]) >= 3
    return cased_words >= len(words) - 1


def _non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _first_email(lines: list[str]) -> str | None:
    for line in lines:
        if match := _EMAIL_PATTERN.search(line):
            return match.group(0)
    return None


def _first_phone(lines: list[str]) -> str | None:
    for line in lines:
        for match in _PHONE_PATTERN.finditer(line):
            candidate = match.group(0).strip()
            if len(re.sub(r"\D", "", candidate)) >= 8:
                return candidate
    return None


def _links_from_contact_lines(lines: list[str]) -> list[str]:
    links: list[str] = []
    for line in lines:
        for match in _LINK_PATTERN.finditer(line):
            link = unwrap_google_redirect_url(match.group(0).rstrip(".)]"))
            if link not in links:
                links.append(link)
    return links


def _unparsed_contact_fragments(line: str) -> list[str]:
    """Return legacy contact text left after removing recognized values."""
    residual = _EMAIL_PATTERN.sub("", line)
    residual = _PHONE_PATTERN.sub(
        lambda match: ""
        if len(re.sub(r"\D", "", match.group(0))) >= 8
        else match.group(0),
        residual,
    )
    residual = _LINK_PATTERN.sub("", residual)

    fragments: list[str] = []
    contact_labels = {
        "email",
        "e-mail",
        "phone",
        "tel",
        "telephone",
        "mobile",
        "website",
        "web",
        "linkedin",
        "github",
    }
    for part in re.split(r"\s*(?:\||•|·|;)\s*", residual):
        fragment = part.strip(" \t|•·;,-")
        if not fragment:
            continue
        if fragment.rstrip(":").strip().casefold() in contact_labels:
            continue
        fragments.append(fragment)
    return fragments


class CVIdentitySourceMap(BaseModel):
    """Source blocks supporting each canonical identity field."""

    full_name: list[str] = Field(default_factory=list)
    headline: list[str] = Field(default_factory=list)
    email: list[str] = Field(default_factory=list)
    phone: list[str] = Field(default_factory=list)
    location: list[str] = Field(default_factory=list)
    links: dict[str, list[str]] = Field(default_factory=dict)

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


class CVIdentity(BaseModel):
    """Canonical candidate identity with a legacy input compatibility bridge.

    ``full_name`` and the structured contact fields are authoritative for new
    documents. ``name`` and ``contact_lines`` remain serialized during the V1
    transition, but they only supply canonical fields that are otherwise empty.
    """

    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)

    source_block_ids: list[str] = Field(default_factory=list)
    field_source_block_ids: CVIdentitySourceMap = Field(
        default_factory=CVIdentitySourceMap,
    )
    hidden_fields: list[str] = Field(
        default_factory=list,
        description="Identity field keys hidden on export/preview (subset of email/phone/location/links/headline).",
    )

    # Legacy fields for backward compatibility. New consumers must prefer the
    # structured fields above.
    name: str = ""
    contact_lines: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def bridge_legacy_identity(cls, data: Any) -> Any:
        """Lift missing canonical fields and mirror canonical values to legacy fields.

        Only unambiguous email, phone, and link values are lifted from legacy
        contact rows; a location is never guessed from free text. Explicit
        canonical values always win.
        """
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        full_name = _non_empty_string(normalized.get("full_name"))
        legacy_name = _non_empty_string(normalized.get("name"))
        headline = _non_empty_string(normalized.get("headline"))

        raw_legacy_contacts = normalized.get("contact_lines")
        if raw_legacy_contacts is not None and not isinstance(
            raw_legacy_contacts, (list, tuple, set)
        ):
            raise ValueError("contact_lines must be a list")
        legacy_contacts = (
            [
                item.strip()
                for item in raw_legacy_contacts
                if isinstance(item, str) and item.strip()
            ]
            if raw_legacy_contacts
            else []
        )

        # -----------------------------------------------------------------
        # Name & Email Swap / Guard Validator:
        # full_name must NEVER be an email. If candidate name matches email,
        # find real name in headline or contact_lines and swap.
        # -----------------------------------------------------------------
        candidate_name = full_name or legacy_name or ""
        if candidate_name and (
            "@" in candidate_name or _EMAIL_PATTERN.search(candidate_name)
        ):
            email_from_name = candidate_name
            real_name: str | None = None

            if headline and _looks_like_person_name(headline):
                real_name = headline
                headline = None
            else:
                for idx, contact in enumerate(legacy_contacts):
                    if _looks_like_person_name(contact):
                        real_name = contact
                        legacy_contacts.pop(idx)
                        break

            if real_name:
                normalized["full_name"] = real_name
                normalized["name"] = real_name
            else:
                normalized["full_name"] = None
                normalized["name"] = ""

            if not normalized.get("email"):
                normalized["email"] = email_from_name
        else:
            if not full_name and legacy_name:
                normalized["full_name"] = legacy_name
                normalized["name"] = legacy_name
            elif not full_name and not legacy_name:
                if (
                    headline
                    and _looks_like_person_name(headline)
                    and not _JOB_TITLE_KEYWORDS.search(headline)
                ):
                    normalized["full_name"] = headline
                    normalized["name"] = headline
                    headline = None
                else:
                    for idx, contact in enumerate(legacy_contacts):
                        if _looks_like_person_name(contact):
                            normalized["full_name"] = contact
                            normalized["name"] = contact
                            legacy_contacts.pop(idx)
                            break
                    if not normalized.get("full_name"):
                        normalized["name"] = ""
            else:
                normalized["name"] = full_name or ""

        if headline:
            normalized["headline"] = headline.rstrip(" /|-,").strip()
        else:
            normalized["headline"] = None

        all_text_sources = [
            *legacy_contacts,
            *(str(v) for v in normalized.values() if isinstance(v, str) and v),
        ]

        email = _non_empty_string(normalized.get("email"))
        if not email:
            email = _first_email(all_text_sources)
            if email:
                normalized["email"] = email

        phone = _non_empty_string(normalized.get("phone"))
        if not phone:
            phone = _first_phone(all_text_sources)
            if phone:
                normalized["phone"] = phone

        raw_links = normalized.get("links")
        if raw_links is not None:
            if not isinstance(raw_links, (list, tuple, set)):
                raise ValueError("links must be a list")
            explicit_links = [
                unwrap_google_redirect_url(item.strip())
                for item in raw_links
                if isinstance(item, str) and item.strip()
            ]
            links = list(dict.fromkeys(explicit_links))
        else:
            links = _links_from_contact_lines(all_text_sources)
        normalized["links"] = links

        canonical_contacts = [
            email,
            phone,
            _non_empty_string(normalized.get("location")),
            *links,
        ]
        residual_legacy_contacts = [
            fragment
            for line in legacy_contacts
            for fragment in _unparsed_contact_fragments(line)
        ]
        normalized["contact_lines"] = list(
            dict.fromkeys(
                [
                    *(value for value in canonical_contacts if value),
                    *residual_legacy_contacts,
                ]
            )
        )

        return normalized

    @model_validator(mode="after")
    def guard_full_name_never_email(self) -> "CVIdentity":
        """Absolute guarantee that full_name and name never contain an email."""
        if self.full_name and (
            "@" in self.full_name or _EMAIL_PATTERN.search(self.full_name)
        ):
            if not self.email:
                self.email = self.full_name
            self.full_name = None
        if self.name and ("@" in self.name or _EMAIL_PATTERN.search(self.name)):
            self.name = ""
        return self

    @model_validator(mode="after")
    def merge_field_provenance(self) -> "CVIdentity":
        """Keep aggregate provenance compatible with the per-field source map."""
        self.source_block_ids = list(
            dict.fromkeys(
                [
                    *self.source_block_ids,
                    *self.field_source_block_ids.all_source_block_ids(),
                ]
            )
        )
        return self

    def canonicalized(self) -> "CVIdentity":
        """Re-run the bridge after legacy fields were mutated in place."""
        return type(self).model_validate(self.model_dump())

    def is_field_hidden(self, key: str) -> bool:
        """Whether a wizard-hidden identity field stays out of export/preview."""
        return key in set(self.hidden_fields or [])

    def canonical_contact_lines(self) -> list[str]:
        """Return canonical contacts plus non-conflicting legacy-only rows."""
        canonical = list(
            dict.fromkeys(
                value
                for value in [self.email, self.phone, self.location, *self.links]
                if value
            )
        )
        residual = [
            fragment
            for line in self.contact_lines
            for fragment in _unparsed_contact_fragments(line)
            if fragment not in canonical
        ]
        return list(dict.fromkeys([*canonical, *residual]))


# ---------------------------------------------------------------------------
# Unmapped Content Schemas
# ---------------------------------------------------------------------------


class LLMUnmappedReference(BaseModel):
    """Unmapped reference returned by the LLM (no server-owned text/page)."""

    block_id: str
    reason: Literal[
        "unknown_section",
        "decorative_content",
        "placeholder_content",
        "ambiguous_content",
    ]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


def deterministic_unmapped_fragment_id(
    block_id: str,
    source_start: int,
    source_end: int,
) -> str:
    """Return a versioned stable ID for one source-derived unmapped span."""
    payload = f"cv-unmapped-v1\x00{block_id}\x00{source_start}\x00{source_end}"
    return f"um1-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


class CVUnmappedContent(BaseModel):
    """Server-populated unmapped content item."""

    block_id: str
    text: str
    page: int = Field(ge=1)
    reason: Literal[
        "unknown_section",
        "decorative_content",
        "placeholder_content",
        "ambiguous_content",
        "parser_omission",
    ]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    fragment_id: str = ""
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def ensure_deterministic_fragment_identity(self) -> "CVUnmappedContent":
        if self.source_start is None and self.source_end is None:
            self.source_start = 0
            self.source_end = len(self.text)
        elif self.source_start is None or self.source_end is None:
            raise ValueError("source_start and source_end must be provided together")
        elif self.source_end < self.source_start:
            raise ValueError("source_end must be greater than or equal to source_start")

        if not self.fragment_id:
            self.fragment_id = deterministic_unmapped_fragment_id(
                self.block_id,
                self.source_start,
                self.source_end,
            )
        return self


# ---------------------------------------------------------------------------
# Document V2
# ---------------------------------------------------------------------------

CURRENT_RECONSTRUCTION_VERSION: int = 4


class CVSourceCoverageIssue(BaseModel):
    """Privacy-safe coverage issue — no raw text, only IDs and counts."""

    code: Literal[
        "unknown_source_reference",
        "substantive_source_omission",
        "duplicate_semantic_ownership",
        "ambiguous_source_match",
        "unmatched_semantic_leaf",
        "invalid_unmapped_reference",
    ]
    block_id: str
    field_paths: list[str] = Field(default_factory=list)
    significant_character_count: int = 0


class CVSourceCoverageDiagnostics(BaseModel):
    """Span-level conservation accounting for the source document."""

    raw_block_count: int = 0
    accounted_block_count: int = 0
    significant_character_count: int = 0
    mapped_character_count: int = 0
    benign_unmapped_character_count: int = 0
    substantive_unmapped_character_count: int = 0
    duplicate_character_count: int = 0
    coverage_ratio: float = 0.0
    issues: list[CVSourceCoverageIssue] = Field(default_factory=list)


class CVReconstructionDiagnostics(BaseModel):
    """Diagnostics returned separately from the user-facing analysis."""

    reconstruction_version: int = CURRENT_RECONSTRUCTION_VERSION
    warnings: list[str] = Field(default_factory=list)
    block_confidence: dict[str, float] = Field(default_factory=dict)
    source_coverage: CVSourceCoverageDiagnostics | None = None


class CVDocumentV2(BaseModel):
    raw_extraction_id: str | None = None
    schema_version: Literal[2] = 2
    extraction_version: str = "2.0"
    parser_version: str = "2.0"
    reconstruction_version: int = CURRENT_RECONSTRUCTION_VERSION
    requires_reprocessing: bool = False
    source_hash: str | None = None
    identity: CVIdentity = Field(default_factory=CVIdentity)
    summary: CVParagraphBlock | None = Field(default=None)
    sections: list[CVSection] = Field(default_factory=list)
    unmapped_content: list[CVUnmappedContent] = Field(default_factory=list)
    reconstruction_warnings: list[str] = Field(default_factory=list)
    reconstruction_diagnostics: CVReconstructionDiagnostics | None = None
    review_attested: bool = Field(
        default=False,
        description=(
            "Set by the review wizard when the candidate has seen the full "
            "rendered document and clicked through (Save & Continue). Marks "
            "explicit human attestation of the document content, which the "
            "reconstruction gate honors for machine-provenance warnings. "
            "Never set by extraction or reconstruction."
        ),
    )

    def to_canonical_dict(self) -> dict[str, Any]:
        """Export CVDocumentV2 to clean canonical machine-readable CV JSON.

        Wizard-hidden bricks and identity fields stay out of the export
        without being deleted from the document.
        """
        ident = self.identity
        result: dict[str, Any] = {
            "identity": {
                "name": ident.full_name or ident.name or None,
                "headline": None
                if ident.is_field_hidden("headline")
                else ident.headline,
                "email": None if ident.is_field_hidden("email") else ident.email,
                "phone": None if ident.is_field_hidden("phone") else ident.phone,
                "location": None
                if ident.is_field_hidden("location")
                else ident.location,
                "links": [] if ident.is_field_hidden("links") else ident.links,
            },
            "summary": self.summary.text
            if self.summary and not self.summary.hidden
            else None,
            "education": [],
            "experience": [],
            "research_experience": [],
            "projects": [],
            "skills": {},
            "publications": [],
            "certifications": [],
            "languages": [],
            "awards": [],
            "activities": [],
            "interests": [],
            "custom": [],
        }

        date_only_re = re.compile(
            r"^(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s*)?"
            r"\b(?:19|20)\d{2}\b(?:\s*[\–\-]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s*)?(?:\b(?:19|20)\d{2}\b|Present|Current|Now))?$",
            re.IGNORECASE,
        )

        for section in self.sections:
            sec_type = (
                section.type.lower() if isinstance(section.type, str) else section.type
            )
            blocks = [block for block in section.blocks if not block.hidden]
            # Rebind the loop below to visible bricks only. Each branch below
            # iterates section.blocks; shadow it once here.
            section = section.model_copy(update={"blocks": blocks})
            if sec_type == "education":
                for block in section.blocks:
                    if isinstance(block, CVEducationBlock):
                        result["education"].append(
                            {
                                "institution": block.institution,
                                "degree": block.degree,
                                "field": block.field,
                                "location": block.location,
                                "date": block.date,
                                "details": block.details,
                                "source": block.source_block_ids,
                            }
                        )
                    elif isinstance(block, CVEntryBlock):
                        result["education"].append(
                            {
                                "institution": block.organization or block.title,
                                "degree": block.subtitle or block.title,
                                "location": block.location,
                                "date": block.date,
                                "details": block.bullets,
                                "source": block.source_block_ids,
                            }
                        )
            elif sec_type in (
                "experience",
                "projects",
                "research_experience",
                "research",
            ):
                sec_title_lower = (section.title or "").lower()
                is_research = "research" in sec_type or "research" in sec_title_lower
                is_projects = "project" in sec_type or "project" in sec_title_lower
                if is_research:
                    target_list = result["research_experience"]
                elif is_projects:
                    target_list = result["projects"]
                else:
                    target_list = result["experience"]
                for block in section.blocks:
                    if isinstance(block, CVEntryBlock):
                        title_val = block.title
                        location_val = block.location
                        org_val = block.organization

                        if (
                            title_val
                            and not _JOB_TITLE_KEYWORDS.search(title_val)
                            and (
                                not location_val
                                or _GEOGRAPHIC_TOKEN_RE.search(title_val)
                            )
                            and re.match(
                                r"^(?:[A-Za-z\s.-]+,\s*[A-Za-z\s.-]+|Remote|Hybrid|On-site)$",
                                title_val.strip(),
                                re.IGNORECASE,
                            )
                            and _GEOGRAPHIC_TOKEN_RE.search(title_val)
                        ):
                            if not location_val:
                                location_val = title_val.strip()
                            if block.subtitle:
                                title_val = block.subtitle
                            elif org_val:
                                title_val = org_val
                                org_val = None

                        bullets_with_source = [
                            {"text": b, "source": block.source_block_ids}
                            for b in block.bullets
                        ]
                        target_list.append(
                            {
                                "title": title_val,
                                "organization": org_val,
                                "location": location_val,
                                "date": block.date,
                                "bullets": bullets_with_source,
                                "source": block.source_block_ids,
                            }
                        )
                    elif isinstance(block, (CVBulletBlock, CVParagraphBlock)):
                        target_list.append(
                            {
                                "title": section.title,
                                "bullets": [
                                    {
                                        "text": block.text,
                                        "source": block.source_block_ids,
                                    }
                                ],
                                "source": block.source_block_ids,
                            }
                        )
            elif sec_type == "skills":
                for block in section.blocks:
                    if isinstance(block, CVSkillGroupBlock):
                        label = block.label or "General"
                        result["skills"][label] = block.skills
                    elif isinstance(block, (CVBulletBlock, CVParagraphBlock)):
                        result["skills"].setdefault("General", []).append(block.text)
            elif sec_type == "publications":
                for block in section.blocks:
                    if isinstance(block, CVPublicationBlock):
                        result["publications"].append(
                            {
                                "title": block.title,
                                "authors": block.authors,
                                "venue": block.venue,
                                "date": block.date,
                                "status": block.status,
                                "source": block.source_block_ids,
                            }
                        )
                    elif isinstance(block, CVEntryBlock):
                        result["publications"].append(
                            {
                                "title": block.title,
                                "authors": block.subtitle,
                                "venue": block.organization,
                                "date": block.date,
                                "source": block.source_block_ids,
                            }
                        )
            elif sec_type == "certifications":
                for block in section.blocks:
                    if isinstance(block, CVEntryBlock):
                        title_clean = block.title.strip()
                        is_date_only = bool(date_only_re.match(title_clean))
                        if is_date_only and result["certifications"]:
                            prev = result["certifications"][-1]
                            if not prev.get("date"):
                                prev["date"] = block.date or title_clean
                            if "source" in prev:
                                prev["source"] = list(
                                    dict.fromkeys(
                                        prev["source"] + block.source_block_ids
                                    )
                                )
                        else:
                            result["certifications"].append(
                                {
                                    "title": block.title,
                                    "organization": block.organization,
                                    "date": block.date,
                                    "source": block.source_block_ids,
                                }
                            )
                    elif isinstance(block, (CVBulletBlock, CVParagraphBlock)):
                        text_clean = block.text.strip()
                        is_date_only = bool(date_only_re.match(text_clean))
                        if is_date_only and result["certifications"]:
                            prev = result["certifications"][-1]
                            if not prev.get("date"):
                                prev["date"] = text_clean
                            if "source" in prev:
                                prev["source"] = list(
                                    dict.fromkeys(
                                        prev["source"] + block.source_block_ids
                                    )
                                )
                        else:
                            result["certifications"].append(
                                {
                                    "title": block.text,
                                    "organization": None,
                                    "date": None,
                                    "source": block.source_block_ids,
                                }
                            )
            elif sec_type in (
                "languages",
                "awards",
                "activities",
                "interests",
                "custom",
            ):
                # Generic list sections (languages / awards / leadership /
                # interests / additional info): never drop — flatten every
                # brick to text so the review wizard + canonical export retain
                # the full source section.
                for block in section.blocks:
                    if isinstance(block, CVEntryBlock):
                        parts = [
                            block.title,
                            block.subtitle,
                            block.organization,
                            block.location,
                            block.date,
                            *block.bullets,
                        ]
                        text = " | ".join(p.strip() for p in parts if p and p.strip())
                        result[sec_type].append(
                            {"text": text, "source": block.source_block_ids}
                        )
                    elif isinstance(block, CVEducationBlock):
                        parts = [
                            block.institution,
                            block.degree,
                            block.field,
                            block.location,
                            block.date,
                            *block.details,
                        ]
                        text = " | ".join(p.strip() for p in parts if p and p.strip())
                        result[sec_type].append(
                            {"text": text, "source": block.source_block_ids}
                        )
                    elif isinstance(block, CVSkillGroupBlock):
                        label = f"{block.label}: " if block.label else ""
                        result[sec_type].append(
                            {
                                "text": f"{label}{', '.join(block.skills)}",
                                "source": block.source_block_ids,
                            }
                        )
                    elif isinstance(block, CVPublicationBlock):
                        parts = [
                            block.authors,
                            block.title,
                            block.venue,
                            block.date,
                            block.status,
                        ]
                        text = " ".join(p.strip() for p in parts if p and p.strip())
                        result[sec_type].append(
                            {"text": text, "source": block.source_block_ids}
                        )
                    elif isinstance(block, (CVBulletBlock, CVParagraphBlock)):
                        result[sec_type].append(
                            {"text": block.text, "source": block.source_block_ids}
                        )
                    elif isinstance(block, CVUnknownBlock):
                        result[sec_type].append(
                            {
                                "text": " | ".join(block.lines),
                                "source": block.source_block_ids,
                            }
                        )

        return result


class StoredCVProcessingResult(BaseModel):
    """Persisted tuple of raw extraction and semantic document."""

    raw_extraction: RawExtraction
    document: CVDocumentV2


class CVRewriteOperation(BaseModel):
    """Operation proposed by the LLM for a specific block field."""

    block_id: str
    field: Literal["text", "bullets", "skills"]
    original_value_hash: str
    proposed_value: str | list[str]


class CVRewriteDecision(BaseModel):
    """Server-owned decision audit for a single proposed rewrite operation."""

    operation_id: str = Field(
        default_factory=lambda: uuid4().hex[:8],
        description="Server-derived hash of block_id, field, and value hashes",
    )
    block_id: str
    field: Literal["text", "bullets", "skills"]
    status: Literal["accepted", "rejected", "preserved"]
    reason_codes: list[str] = Field(default_factory=list)
    original_value_hash: str
    proposed_value_hash: str


class CVTailoringDiagnostics(BaseModel):
    """Server-owned audit accounting for all tailoring rewrite decisions.

    Kept outside CVDocumentV2 to preserve clean candidate document semantics.
    """

    rewrite_version: int = 1
    source_document_hash: str
    jd_hash: str
    accepted_count: int = 0
    rejected_count: int = 0
    preserved_count: int = 0
    used_fallback: bool = False
    decisions: list[CVRewriteDecision] = Field(default_factory=list)


@dataclass
class CVTailoringResult:
    source_document: CVDocumentV2
    tailored_document: CVDocumentV2
    diagnostics: CVTailoringDiagnostics
    tailoring_entitlement: str


class CVBlockRewrite(BaseModel):
    """Legacy block-ID rewrite candidate (retained for backward compatibility)."""

    block_id: str
    text: str | None = None
    bullets: list[str] | None = None
    skills: list[str] | None = None
    preserve: bool = False
