"""Tests for the V1→V2 compatibility adapter."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.models.cv_document_v2 import (
    CVEducationBlock,
    CVEntryBlock,
    CVPublicationBlock,
    CVSkillGroupBlock,
)
from app.models.domain import ExperienceItem, TailoredCV, TailoredCVSection
from app.services.cv_v1_adapter import v1_to_v2, v1_to_v2_safe

ROOT = Path(__file__).resolve().parents[2]


def _make_cv(**overrides) -> TailoredCV:
    defaults = TailoredCV(
        name="Nguyen Duy",
        headline="Software Engineer",
        contact_lines=["duy@example.com", "linkedin.com/in/duy"],
        summary="Experienced engineer.",
        sections=[],
        experience=[],
        skills=[],
        education="",
    )
    for k, v in overrides.items():
        setattr(defaults, k, v)
    return defaults


class TestIdentityMapping:
    def test_preserves_identity_fields(self):
        cv = _make_cv(name="Test Name", headline="CTO", contact_lines=["a@b.com"])
        result = v1_to_v2(cv)
        assert result.schema_version == 2
        assert result.identity.name == "Test Name"
        assert result.identity.headline == "CTO"
        assert "a@b.com" in result.identity.contact_lines
        assert result.reconstruction_version == 1
        assert result.requires_reprocessing is True

    def test_empty_name_is_fine(self):
        cv = _make_cv(name="")
        result = v1_to_v2(cv)
        assert result.identity.name == ""


class TestSectionClassification:
    def test_experience_section(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(title="Work Experience", items=["Engineer at ABC"]),
            ],
        )
        result = v1_to_v2(cv)
        assert len(result.sections) == 1
        assert result.sections[0].type == "experience"

    def test_projects_section(self):
        cv = _make_cv(
            sections=[TailoredCVSection(title="Projects", items=["Project A"])],
        )
        result = v1_to_v2(cv)
        assert result.sections[0].type == "projects"

    def test_skills_section(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(title="Technical Skills", items=["React", "Node.js"]),
            ],
        )
        result = v1_to_v2(cv)
        assert result.sections[0].type == "skills"

    def test_education_section(self):
        cv = _make_cv(
            sections=[TailoredCVSection(title="Education", items=["Bachelor's"])],
        )
        result = v1_to_v2(cv)
        assert result.sections[0].type == "education"

    def test_publications_section(self):
        cv = _make_cv(
            sections=[TailoredCVSection(title="Publications", items=["Paper title"])],
        )
        result = v1_to_v2(cv)
        assert result.sections[0].type == "publications"

    def test_vietnamese_experience(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Kinh nghiệm làm việc",
                    items=["Engineer at XYZ"],
                ),
            ],
        )
        result = v1_to_v2(cv)
        assert result.sections[0].type == "experience"

    def test_vietnamese_skills(self):
        cv = _make_cv(sections=[TailoredCVSection(title="Kỹ năng", items=["Python"])])
        result = v1_to_v2(cv)
        assert result.sections[0].type == "skills"

    def test_unknown_section_becomes_custom(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Community Contributions",
                    items=["Volunteering"],
                ),
            ],
        )
        result = v1_to_v2(cv)
        assert result.sections[0].type == "custom"


class TestSkillParsing:
    def test_labeled_skill_groups(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Technical Skills",
                    items=[
                        "AI/ML Research: PyTorch, Transformers, GNN",
                        "Development: React, Node.js, FastAPI",
                    ],
                ),
            ],
        )
        result = v1_to_v2(cv)
        skill_blocks = [
            b for b in result.sections[0].blocks if isinstance(b, CVSkillGroupBlock)
        ]
        assert len(skill_blocks) >= 2
        labels = {b.label for b in skill_blocks if b.label}
        assert "AI/ML Research" in labels
        assert "Development" in labels

    def test_flat_skills_become_single_group(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(title="Skills", items=["React", "Python", "Go"]),
            ],
        )
        result = v1_to_v2(cv)
        skill_blocks = [
            b for b in result.sections[0].blocks if isinstance(b, CVSkillGroupBlock)
        ]
        assert len(skill_blocks) == 1
        assert len(skill_blocks[0].skills) == 3

    def test_mixed_skill_groups_preserve_loose_skills(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Skills",
                    items=["Languages: Python, Go", "Docker"],
                ),
            ],
        )

        result = v1_to_v2(cv)
        serialized = str(result.sections[0].model_dump())

        assert "Python" in serialized
        assert "Go" in serialized
        assert "Docker" in serialized


class TestEntryDetection:
    def test_experience_entries(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Work Experience",
                    items=[
                        "Software Engineer — ABC Corp",
                        "• Built backend APIs",
                        "• Optimized database queries",
                        "Data Scientist — XYZ Inc",
                        "• Built ML models",
                    ],
                ),
            ],
        )
        result = v1_to_v2(cv)
        entry_blocks = [
            b for b in result.sections[0].blocks if isinstance(b, CVEntryBlock)
        ]
        assert len(entry_blocks) == 2
        assert "ABC Corp" in entry_blocks[0].title
        assert "XYZ Inc" in entry_blocks[1].title

    def test_wrapped_bullets_are_joined(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Projects",
                    items=[
                        "Project A — Tech Corp",
                        "• Built a system that handles millions of requests",
                        "  per second across multiple regions",
                    ],
                ),
            ],
        )
        result = v1_to_v2(cv)
        entry_blocks = [
            b for b in result.sections[0].blocks if isinstance(b, CVEntryBlock)
        ]
        assert len(entry_blocks) == 1
        assert "per second" in entry_blocks[0].bullets[0]


class TestSummaryHandling:
    def test_summary_becomes_paragraph_block(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(title="Summary", items=["Experienced engineer."]),
            ],
        )
        result = v1_to_v2(cv)
        summary = result.summary
        assert summary is not None
        assert summary.text == "Experienced engineer."

    def test_summary_items_are_not_treated_as_section(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(title="Summary", items=["Experienced engineer."]),
            ],
        )
        result = v1_to_v2(cv)
        summary_types = [s.type for s in result.sections]
        assert "summary" not in summary_types

    def test_distinct_summary_section_content_is_preserved(self):
        cv = _make_cv(
            summary="Top-level summary.",
            sections=[
                TailoredCVSection(
                    title="Summary",
                    items=["Additional summary detail."],
                ),
            ],
        )

        result = v1_to_v2(cv)

        assert result.summary is not None
        assert "Top-level summary." in result.summary.text
        assert "Additional summary detail." in result.summary.text


class TestConservativeEducationParsing:
    def test_uncertain_education_content_is_not_promoted_to_entry(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Education",
                    items=["Coursework in distributed systems."],
                ),
            ],
        )

        result = v1_to_v2(cv)

        assert isinstance(result.sections[0].blocks[0], CVEducationBlock)

    def test_education_details_after_heading_remain_unhighlighted(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Education",
                    items=["University — 2024", "Coursework in distributed systems."],
                ),
            ],
        )

        result = v1_to_v2(cv)
        block = result.sections[0].blocks[0]

        assert isinstance(block, CVEducationBlock)
        assert block.institution == "University — 2024"
        assert block.details == ["Coursework in distributed systems."]

    def test_dated_education_prose_is_not_promoted_to_institution(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Education",
                    items=["Graduated with honors in 2020"],
                ),
            ],
        )

        result = v1_to_v2(cv)
        block = result.sections[0].blocks[0]

        assert isinstance(block, CVEducationBlock)
        assert block.institution is None
        assert block.details == ["Graduated with honors in 2020"]

    @pytest.mark.parametrize(
        "prose",
        [
            "Completed university coursework in 2020",
            "Studied at Example University",
            "Research conducted at Example University",
            "Learning at Example University",
        ],
    )
    def test_education_prose_with_institution_token_stays_unhighlighted(
        self,
        prose: str,
    ):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Education",
                    items=[prose],
                ),
            ],
        )

        result = v1_to_v2(cv)
        block = result.sections[0].blocks[0]

        assert isinstance(block, CVEducationBlock)
        assert block.institution is None
        assert block.details == [prose]


class TestStableIds:
    def test_repeated_adaptation_has_deterministic_ids(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Projects",
                    items=["Project A — Tech Corp", "• Built APIs"],
                ),
            ],
        )

        first = v1_to_v2(cv)
        second = v1_to_v2(cv)

        assert first.sections[0].id == second.sections[0].id
        assert (
            first.sections[0].blocks[0].block_id
            == second.sections[0].blocks[0].block_id
        )


class TestEmptyFallback:
    def test_empty_cv(self):
        cv = TailoredCV(name="")
        result = v1_to_v2(cv)
        assert result.schema_version == 2
        assert result.sections == []
        assert result.summary is None

    def test_legacy_experience_field(self):
        cv = TailoredCV(
            name="Duy",
            experience=[
                ExperienceItem(
                    company="ABC",
                    role="Engineer",
                    bullet_points=["Built APIs"],
                ),
            ],
            skills=["React"],
            education="Bachelor's in CS",
        )
        result = v1_to_v2(cv)
        assert len(result.sections) >= 1
        types = [s.type for s in result.sections]
        assert "experience" in types
        assert "skills" in types
        assert "education" in types


class TestSafety:
    def test_content_never_discarded(self):
        """Every item from the original V1 document must appear in V2 output."""
        items = [
            "Project A — Tech Corp",
            "• Built a system",
            "• Optimized queries",
            "• Wrote documentation",
        ]
        cv = _make_cv(sections=[TailoredCVSection(title="Projects", items=items)])
        result = v1_to_v2(cv)
        text = " ".join(str(b.model_dump()) for b in result.sections[0].blocks).lower()
        assert "built a system" in text
        assert "optimized queries" in text
        assert "documentation" in text

    def test_v1_to_v2_safe_returns_none_for_none(self):
        assert v1_to_v2_safe(None) is None


class TestPublicationParsing:
    def test_publication_becomes_publication_block(self):
        cv = _make_cv(
            sections=[
                TailoredCVSection(
                    title="Publications",
                    items=["Deep Learning for Video Retrieval"],
                ),
            ],
        )
        result = v1_to_v2(cv)
        pub_blocks = [
            b for b in result.sections[0].blocks if isinstance(b, CVPublicationBlock)
        ]
        assert len(pub_blocks) == 1
        assert "Deep Learning" in pub_blocks[0].title


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_frontend_v1_adapter_marks_document_for_reprocessing() -> None:
    module = (ROOT / "frontend/src/lib/cv-v1-to-v2-adapter.ts").as_uri()
    script = (
        f"import {{ v1ToV2 }} from {json.dumps(module)};"
        'const document = v1ToV2("Legacy Candidate", "Engineer", '
        '["legacy@example.com | +84 912 345 678 | Ha Noi, Vietnam"], "Summary");'
        "process.stdout.write(JSON.stringify(document));"
    )
    completed = subprocess.run(
        [
            "node",
            "--no-warnings",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    document = json.loads(completed.stdout)

    assert document["reconstruction_version"] == 1
    assert document["requires_reprocessing"] is True
    assert document["identity"]["full_name"] == "Legacy Candidate"
    assert document["identity"]["email"] == "legacy@example.com"
    assert document["identity"]["phone"] == "+84 912 345 678"
    assert document["identity"]["location"] is None
    assert document["identity"]["contact_lines"].count("legacy@example.com") == 1
    assert document["identity"]["contact_lines"].count("+84 912 345 678") == 1
    assert document["identity"]["contact_lines"].count("Ha Noi, Vietnam") == 1


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_frontend_renderer_prefers_canonical_identity_over_legacy_conflicts() -> None:
    module = (ROOT / "frontend/src/lib/cv-render-html.ts").as_uri()
    document = {
        "identity": {
            "full_name": "Canonical Candidate",
            "name": "Stale Legacy Name",
            "headline": None,
            "email": "canonical@example.com",
            "phone": "+84 912 345 678",
            "location": None,
            "links": [],
            "contact_lines": [
                "canonical@example.com | +84 912 345 678 | Ha Noi, Vietnam"
            ],
        },
        "summary": None,
        "sections": [],
    }
    script = (
        f"import {{ buildCVHtml }} from {json.dumps(module)};"
        f"const document = {json.dumps(document)};"
        'process.stdout.write(buildCVHtml(document, "classic_ats", "en"));'
    )
    completed = subprocess.run(
        [
            "node",
            "--no-warnings",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Canonical Candidate" in completed.stdout
    assert completed.stdout.count("canonical@example.com") == 1
    assert completed.stdout.count("+84 912 345 678") == 1
    assert completed.stdout.count("Ha Noi, Vietnam") == 1
    assert "Stale Legacy Name" not in completed.stdout
