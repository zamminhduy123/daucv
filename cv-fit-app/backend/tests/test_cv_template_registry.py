"""Unit tests for Phase 6 server-owned template registry."""

import pytest

from app.services.cv_template_registry import (
    UnknownTemplateError,
    UnsupportedTemplateVersionError,
    get_template_package,
    list_templates,
    resolve_template_id,
)


def test_list_templates_returns_allowlisted_templates():
    templates = list_templates()
    ids = [t.template_id for t in templates]
    assert "classic_ats" in ids
    assert "modern_professional" in ids
    assert "compact" in ids


def test_resolve_template_id_maps_legacy_values():
    assert resolve_template_id("classic_ats") == "classic_ats"
    assert resolve_template_id("modern_professional") == "modern_professional"
    assert resolve_template_id("compact_one_page") == "compact"
    assert resolve_template_id("compact") == "compact"


def test_resolve_template_id_rejects_unknown():
    with pytest.raises(
        UnknownTemplateError, match="Unknown or unsupported template ID"
    ):
        resolve_template_id("invalid_template_xyz")


def test_get_template_package_resolves_active_css():
    definition, css_path = get_template_package("classic_ats")
    assert definition.template_id == "classic_ats"
    assert definition.version == 1
    assert css_path.exists()
    assert "Liberation Sans" in css_path.read_text(encoding="utf-8")


def test_get_template_package_rejects_unsupported_version():
    with pytest.raises(UnsupportedTemplateVersionError):
        get_template_package("classic_ats", version=999)
