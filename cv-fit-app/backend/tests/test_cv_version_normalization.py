"""Tests for version-aware loading (Phase 2, Step 2.3)."""

from datetime import UTC, datetime

import pytest

from app.models.cv_document_v2 import CVDocumentV2
from app.services.tailored_cv_service import (
    UnsupportedCVSchemaVersionError,
    normalize_version,
)

_NOW = datetime.now(UTC)


def _defaults(**overrides) -> dict:
    base = {
        "selected_design": "classic_ats",
        "created_at": _NOW,
        "updated_at": _NOW,
        "jd_text": "",
        "id": "00000000-0000-0000-0000-000000000000",
    }
    base.update(overrides)
    return base


def _make_v2_doc(**overrides) -> CVDocumentV2:
    return CVDocumentV2(
        schema_version=2,
        identity=overrides.get("identity", {}),
        summary=overrides.get("summary"),
        sections=overrides.get("sections", []),
    )


class TestNormalizeVersionV2:
    def test_v2_document_passed_through(self):
        v2_doc = _make_v2_doc()
        result = normalize_version(
            tailored_cv_data={
                "name": "Duy",
                "sections": [],
                "experience": [],
                "skills": [],
                "education": "",
            },
            document_v2_data=v2_doc.model_dump(),
            schema_version=2,
            **_defaults(),
        )
        assert result.document_v2 is not None
        assert result.document_schema_version == 2

    def test_v2_document_preserves_schema_version(self):
        v2_doc = _make_v2_doc()
        result = normalize_version(
            tailored_cv_data={
                "name": "Duy",
                "sections": [],
                "experience": [],
                "skills": [],
                "education": "",
            },
            document_v2_data=v2_doc.model_dump(),
            schema_version=2,
            **_defaults(),
        )
        assert result.document_schema_version == 2


class TestNormalizeVersionV1:
    def test_v1_without_document_v2_gets_adapter(self):
        """V1 records without document_v2 get a V2 from the adapter."""
        result = normalize_version(
            tailored_cv_data={
                "name": "Duy",
                "sections": [{"title": "Projects", "items": ["Project A"]}],
                "experience": [],
                "skills": [],
                "education": "",
            },
            document_v2_data=None,
            schema_version=1,
            **_defaults(),
        )
        assert result.document_schema_version == 1  # stored version preserved
        assert result.document_v2 is not None
        assert result.document_v2.schema_version == 2

    def test_v1_ignores_stale_document_v2_payload(self):
        result = normalize_version(
            tailored_cv_data={
                "name": "V1 source",
                "sections": [],
                "experience": [],
                "skills": [],
                "education": "",
            },
            document_v2_data=_make_v2_doc(
                identity={"name": "Stale V2 payload"},
            ).model_dump(),
            schema_version=1,
            **_defaults(),
        )

        assert result.document_v2 is not None
        assert result.document_v2.identity.name == "V1 source"

    def test_v1_adapter_preserves_identity(self):
        result = normalize_version(
            tailored_cv_data={
                "name": "Test User",
                "headline": "Engineer",
                "contact_lines": ["a@b.com"],
                "summary": "Experienced.",
                "sections": [],
                "experience": [],
                "skills": [],
                "education": "",
            },
            document_v2_data=None,
            schema_version=1,
            **_defaults(),
        )
        v2 = result.document_v2
        assert v2 is not None
        assert v2.identity.name == "Test User"
        assert v2.summary is not None
        assert v2.summary.text == "Experienced."

    def test_v1_adapter_classifies_sections(self):
        result = normalize_version(
            tailored_cv_data={
                "name": "Duy",
                "sections": [
                    {"title": "Work Experience", "items": ["Engineer at ABC"]},
                ],
                "experience": [],
                "skills": [],
                "education": "",
            },
            document_v2_data=None,
            schema_version=1,
            **_defaults(),
        )
        v2 = result.document_v2
        assert v2 is not None
        assert len(v2.sections) == 1
        assert v2.sections[0].type == "experience"

    def test_v1_adapter_derives_from_legacy_fields(self):
        result = normalize_version(
            tailored_cv_data={
                "name": "Duy",
                "sections": [],
                "experience": [
                    {
                        "company": "ABC",
                        "role": "Engineer",
                        "bullet_points": ["Built APIs"],
                    },
                ],
                "skills": ["React"],
                "education": "Bachelor's in CS",
            },
            document_v2_data=None,
            schema_version=1,
            **_defaults(),
        )
        v2 = result.document_v2
        assert v2 is not None
        types = [s.type for s in v2.sections]
        assert "experience" in types
        assert "skills" in types
        assert "education" in types


class TestNormalizeVersionEmpty:
    def test_empty_tailored_cv(self):
        result = normalize_version(
            tailored_cv_data={
                "name": "",
                "sections": [],
                "experience": [],
                "skills": [],
                "education": "",
            },
            document_v2_data=None,
            schema_version=1,
            **_defaults(),
        )
        assert result.document_v2 is not None
        assert result.document_v2.identity.name == ""


def test_future_schema_version_is_rejected() -> None:
    with pytest.raises(UnsupportedCVSchemaVersionError, match="schema version: 3"):
        normalize_version(
            tailored_cv_data={"name": "Duy", "sections": []},
            document_v2_data=None,
            schema_version=3,
            **_defaults(),
        )
