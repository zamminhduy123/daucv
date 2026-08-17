from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_template import CVTemplateDefinition
from app.services.cv_template_placement import build_placement_manifest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
CURRENT_RENDER_VERSION = 1


@dataclass(frozen=True)
class TemplatePackage:
    template_id: str
    template_version: int
    render_version: int
    definition: CVTemplateDefinition
    render_function: Callable[[CVDocumentV2, str, int | None, str], Any]
    placement_function: Callable[[CVDocumentV2, CVTemplateDefinition], Any]
    css_path: Path
    font_assets: dict[str, Path]

    def __iter__(self):
        yield self.definition
        yield self.css_path


# Registry of allowlisted templates and their latest active versions
_TEMPLATE_CATALOG: dict[str, CVTemplateDefinition] = {
    "classic_ats": CVTemplateDefinition(
        template_id="classic_ats",
        version=1,
        label="Classic ATS",
        description="Single-column ATS-friendly traditional template with high readability.",
        layout="single_column",
        ats_friendly=True,
        supports_multipage=True,
    ),
    "modern_professional": CVTemplateDefinition(
        template_id="modern_professional",
        version=1,
        label="Modern Professional",
        description="Clean two-column layout separating skills/education into a sidebar.",
        layout="sidebar",
        ats_friendly=True,
        supports_multipage=True,
    ),
    "compact": CVTemplateDefinition(
        template_id="compact",
        version=1,
        label="Compact",
        description="Dense layout for maximum information density; paginates smoothly when long.",
        layout="single_column",
        ats_friendly=True,
        supports_multipage=True,
    ),
}

# Legacy template ID mapping for backward compatibility with pre-Phase 6 records
_LEGACY_MAP: dict[str, str] = {
    "classic_ats": "classic_ats",
    "modern_professional": "modern_professional",
    "compact_one_page": "compact",
    "compact": "compact",
}


class UnknownTemplateError(ValueError):
    """Raised when an unrecognized template_id is requested."""

    def __init__(self, template_id: str) -> None:
        super().__init__(f"Unknown or unsupported template ID: '{template_id}'.")
        self.template_id = template_id


class UnsupportedTemplateVersionError(ValueError):
    """Raised when an unsupported template_version is requested."""

    def __init__(self, template_id: str, version: int) -> None:
        super().__init__(
            f"Unsupported template version {version} for template '{template_id}'."
        )
        self.template_id = template_id
        self.version = version


def resolve_template_id(template_id: str) -> str:
    """Normalize legacy or active template_id to canonical registry key."""
    canonical = _LEGACY_MAP.get(template_id, template_id)
    if canonical not in _TEMPLATE_CATALOG:
        raise UnknownTemplateError(template_id)
    return canonical


def get_template_definition(template_id: str) -> CVTemplateDefinition:
    """Get the active CVTemplateDefinition for a given template_id."""
    canonical_id = resolve_template_id(template_id)
    return _TEMPLATE_CATALOG[canonical_id]


def list_templates() -> list[CVTemplateDefinition]:
    """Return list of all registered active templates."""
    return list(_TEMPLATE_CATALOG.values())


def get_template_package(
    template_id: str,
    version: int | None = None,
) -> TemplatePackage:
    """Resolve immutable TemplatePackage tuple for (template_id, version)."""
    canonical_id = resolve_template_id(template_id)
    definition = _TEMPLATE_CATALOG[canonical_id]
    target_version = version if version is not None else definition.version

    if target_version != definition.version:
        version_dir = TEMPLATES_DIR / canonical_id / f"v{target_version}"
        if not version_dir.exists():
            raise UnsupportedTemplateVersionError(canonical_id, target_version)

    css_path = TEMPLATES_DIR / canonical_id / f"v{target_version}" / "style.css"
    if not css_path.exists():
        raise UnsupportedTemplateVersionError(canonical_id, target_version)

    font_assets: dict[str, Path] = {}
    if FONTS_DIR.exists():
        for font_file in FONTS_DIR.glob("*.ttf"):
            font_assets[font_file.stem] = font_file

    from app.services.cv_template_render_service import render_cv_document

    return TemplatePackage(
        template_id=canonical_id,
        template_version=target_version,
        render_version=CURRENT_RENDER_VERSION,
        definition=definition,
        render_function=render_cv_document,
        placement_function=build_placement_manifest,
        css_path=css_path,
        font_assets=font_assets,
    )
