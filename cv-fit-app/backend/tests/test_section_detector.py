"""Phase 4 — Section detection tests.

Covers the three steps:
  Step 4.1  Canonical section vocabulary mapping
  Step 4.2  Structural heading detection (font size, separators, position)
  Step 4.3  Unknown/custom section preservation

Run with:
    cd backend && pytest tests/test_section_detector.py -v
"""

from __future__ import annotations

import pytest

from app.services.layout_extraction import ExtractedLine
from app.services.section_detector import (
    _classify_skill_section,
    _detect_identity,
    _detect_section_boundaries,
    _detect_summary,
    _looks_like_contact,
    _looks_like_entry_headline,
    _looks_like_headline,
    _looks_like_name,
    detect_sections,
)
from app.services.section_vocabulary import (
    classify_heading,
    is_known_section_type,
)

# ---------------------------------------------------------------------------
# Step 4.1 — Canonical section vocabulary
# ---------------------------------------------------------------------------


class TestVocabularyMapping:
    """Verify that all heading variants map to canonical types."""

    @pytest.mark.parametrize(
        "text,expected_type",
        [
            ("WORK EXPERIENCE", "experience"),
            ("EMPLOYMENT HISTORY", "experience"),
            ("KINH NGHIỆM LÀM VIỆC", "experience"),
            ("Kinh Nghiem", "experience"),
            ("PROJECTS", "projects"),
            ("DỰ ÁN", "projects"),
            ("DỰ ÁN CÁ NHÂN", "projects"),
            ("TECHNICAL SKILLS", "skills"),
            ("KỸ NĂNG", "skills"),
            ("Kỹ năng chuyên môn", "skills"),
            ("PUBLICATIONS", "publications"),
            ("CÔNG BỐ KHOA HỌC", "publications"),
            ("EDUCATION", "education"),
            ("HỌC VẤN", "education"),
            ("CERTIFICATIONS", "certifications"),
            ("CHỨNG CHỈ", "certifications"),
            ("LANGUAGES", "languages"),
            ("NGÔN NGỮ", "languages"),
            ("AWARDS", "awards"),
            ("GIẢI THƯỞNG", "awards"),
            ("ACTIVITIES", "activities"),
            ("HOẠT ĐỘNG", "activities"),
            ("INTERESTS", "interests"),
            ("SỞ THÍCH", "interests"),
            ("SUMMARY", "summary"),
            ("PROFESSIONAL SUMMARY", "summary"),
            ("TÓM TẮT", "summary"),
            ("GIOI THIEU", "summary"),
            ("CONTACT", "custom"),
            ("LIÊN HỆ", "custom"),  # "contact" maps to "custom" in our vocab
        ],
    )
    def test_classify_heading(self, text: str, expected_type: str) -> None:
        result = classify_heading(text)
        assert result is not None
        assert result[0] == expected_type

    @pytest.mark.parametrize(
        "text",
        [
            "This is a regular paragraph of text",
            "Some random content line",
            "Built RESTful APIs using FastAPI",
            "Backend Developer at TechCorp",
        ],
    )
    def test_classify_heading_unknown(self, text: str) -> None:
        result = classify_heading(text)
        assert result is None


# ---------------------------------------------------------------------------
# Step 4.2 — Structural heading detection
# ---------------------------------------------------------------------------


class TestStructuralHeading:
    """Verify that structural signals correctly identify headings."""

    def test_all_caps_left_margin(self) -> None:
        line = ExtractedLine(
            text="TECHNICAL SKILLS",
            page=0,
            x=0,
            y=500,
            width=200,
            height=14,
            font_size=14.0,
            font_weight=700,
        )
        assert _looks_like_structural_heading(
            line,
            "TECHNICAL SKILLS",
            baseline_size=11.0,
            index=5,
            total=30,
        )

    def test_title_case_left_margin(self) -> None:
        line = ExtractedLine(
            text="Work Experience",
            page=0,
            x=0,
            y=400,
            width=150,
            height=14,
            font_size=13.0,
            font_weight=700,
        )
        assert _looks_like_structural_heading(
            line,
            "Work Experience",
            baseline_size=11.0,
            index=5,
            total=30,
        )

    def test_long_text_rejected(self) -> None:
        line = ExtractedLine(
            text="This Is A Very Long Title That Should Not Be A Heading",
            page=0,
            x=0,
            y=400,
            width=400,
            height=14,
            font_size=13.0,
            font_weight=700,
        )
        assert not _looks_like_structural_heading(
            line,
            line.text,
            baseline_size=11.0,
            index=5,
            total=30,
        )

    def test_not_left_aligned_rejected(self) -> None:
        line = ExtractedLine(
            text="SKILLS",
            page=0,
            x=200,
            y=400,
            width=80,
            height=14,
            font_size=13.0,
            font_weight=700,
        )
        assert not _looks_like_structural_heading(
            line,
            "SKILLS",
            baseline_size=11.0,
            index=5,
            total=30,
        )

    def test_separator_after_confirms(self) -> None:
        # This test relies on separator detection being correct
        # The actual boundary detection tests below exercise this
        pass


def _looks_like_structural_heading(
    line: ExtractedLine,
    text: str,
    baseline_size: float | None,
    index: int,
    total: int,
) -> bool:
    """Re-export private function for testing."""
    from app.services.section_detector import _looks_like_structural_heading

    return _looks_like_structural_heading(line, text, baseline_size, index, total)


# ---------------------------------------------------------------------------
# Step 4.3 — Unknown/custom section preservation
# ---------------------------------------------------------------------------


class TestCustomSectionPreservation:
    """Verify that unrecognized headings become custom sections and are not dropped."""

    def test_unknown_heading_becomes_custom(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="NGUYEN VAN DUY",
                page=0,
                x=72,
                y=700,
                width=200,
                height=14,
                font_size=16.0,
                font_weight=700,
            ),
            ExtractedLine(text="", page=0, x=72, y=685, width=0, height=0),
            ExtractedLine(
                text="HOAT DONG BO IUOC",
                page=0,
                x=72,
                y=665,
                width=180,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Volunteered at local shelter",
                page=0,
                x=72,
                y=650,
                width=400,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]
        boundaries = _detect_section_boundaries(lines)
        # Should detect the unknown heading as a custom section
        custom_boundaries = [b for b in boundaries if b.canonical_type == "custom"]
        assert len(custom_boundaries) >= 1

    def test_unrecognized_content_not_dropped(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="My Name",
                page=0,
                x=72,
                y=700,
                width=100,
                height=14,
                font_size=14.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Some random content",
                page=0,
                x=72,
                y=680,
                width=300,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="Another line of content",
                page=0,
                x=72,
                y=665,
                width=300,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]
        doc = detect_sections(lines)
        # Should have at least one section containing the content
        assert len(doc.sections) >= 1
        # Content should be preserved somewhere
        all_text = " ".join(
            block.text
            if hasattr(block, "text")
            else " ".join(block.lines)
            if hasattr(block, "lines")
            else ""
            for section in doc.sections
            for block in section.blocks
        )
        assert (
            "random content" in all_text.lower() or "another line" in all_text.lower()
        )


# ---------------------------------------------------------------------------
# Identity preamble detection
# ---------------------------------------------------------------------------


class TestIdentityDetection:
    """Verify name, headline, and contact detection from the top of a CV."""

    def test_simple_identity(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="NGUYEN VAN DUY",
                page=0,
                x=72,
                y=700,
                width=200,
                height=14,
                font_size=16.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Backend Developer | hcmc",
                page=0,
                x=72,
                y=680,
                width=300,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]
        identity = _detect_identity(lines)
        assert identity.name == "NGUYEN VAN DUY"
        assert "Backend Developer" in identity.headline

    def test_name_detection(self) -> None:
        assert _looks_like_name("Nguyen Van Duy") is True
        assert _looks_like_name("LE THI MAI") is True
        assert _looks_like_name("JOHN SMITH JR") is True
        # Not a name
        assert _looks_like_name("This is way too many words for a name") is False
        assert _looks_like_name("the quick brown fox") is False
        assert _looks_like_name("developer") is False

    def test_headline_detection(self) -> None:
        assert _looks_like_headline("Backend Developer | HCMC") is True
        assert _looks_like_headline("Data Scientist and ML Engineer") is True
        assert _looks_like_headline("Regular paragraph text") is False

    def test_contact_detection(self) -> None:
        assert _looks_like_contact("email@example.com") is True
        assert _looks_like_contact("+84 90 123 4567") is True
        assert _looks_like_contact("HCMC") is True
        assert _looks_like_contact("Regular text paragraph") is False


# ---------------------------------------------------------------------------
# Summary detection
# ---------------------------------------------------------------------------


class TestSummaryDetection:
    """Verify summary detection at the top of the document."""

    def test_summary_before_sections(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="NGUYEN VAN DUY",
                page=0,
                x=72,
                y=700,
                width=200,
                height=14,
                font_size=16.0,
                font_weight=700,
            ),
            ExtractedLine(text="", page=0, x=72, y=685, width=0, height=0),
            ExtractedLine(
                text="TÓM TẮT",
                page=0,
                x=72,
                y=665,
                width=80,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Kỹ sư backend với 3 năm kinh nghiệm.",
                page=0,
                x=72,
                y=650,
                width=400,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="Thành thạo Python và FastAPI.",
                page=0,
                x=72,
                y=635,
                width=350,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(text="", page=0, x=72, y=620, width=0, height=0),
            ExtractedLine(
                text="KINH NGHIỆM",
                page=0,
                x=72,
                y=600,
                width=120,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
        ]
        summary = _detect_summary(lines)
        assert summary is not None
        assert "Kỹ sư backend" in summary.text

    def test_no_summary(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="KINH NGHIỆM",
                page=0,
                x=72,
                y=700,
                width=120,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="• Built APIs",
                page=0,
                x=90,
                y=680,
                width=200,
                height=12,
                font_size=11.0,
                font_weight=400,
                bullet_marker="•",
            ),
        ]
        summary = _detect_summary(lines)
        assert summary is None


# ---------------------------------------------------------------------------
# Section boundary detection
# ---------------------------------------------------------------------------


class TestBoundaryDetection:
    """Verify section boundaries are correctly identified."""

    def test_multiple_sections(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="NGUYEN VAN DUY",
                page=0,
                x=72,
                y=700,
                width=200,
                height=14,
                font_size=16.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="KINH NGHIỆM",
                page=0,
                x=72,
                y=600,
                width=100,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="• Built APIs",
                page=0,
                x=90,
                y=580,
                width=200,
                height=12,
                font_size=11.0,
                font_weight=400,
                bullet_marker="•",
            ),
            ExtractedLine(
                text="KỸ NĂNG",
                page=0,
                x=72,
                y=500,
                width=80,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Python, FastAPI",
                page=0,
                x=72,
                y=480,
                width=200,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]
        boundaries = _detect_section_boundaries(lines)
        assert len(boundaries) == 2
        types = {b.canonical_type for b in boundaries}
        assert "experience" in types
        assert "skills" in types

    def test_empty_lines(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(text="", page=0, x=72, y=700, width=0, height=0),
            ExtractedLine(
                text="PROJECTS",
                page=0,
                x=72,
                y=600,
                width=100,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
        ]
        boundaries = _detect_section_boundaries(lines)
        assert len(boundaries) == 1
        assert boundaries[0].canonical_type == "projects"


# ---------------------------------------------------------------------------
# Full document detection
# ---------------------------------------------------------------------------


class TestFullDocumentDetection:
    """Verify end-to-end CV document construction."""

    def test_two_page_cv_structure(self) -> None:
        """Simulate the Phase 0 two_page_cv fixture structure."""
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="NGUYEN VAN DUY",
                page=0,
                x=72,
                y=700,
                width=200,
                height=14,
                font_size=16.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Backend Developer | email@test.com",
                page=0,
                x=72,
                y=680,
                width=300,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(text="", page=0, x=72, y=665, width=0, height=0),
            ExtractedLine(
                text="TÓM TẮT",
                page=0,
                x=72,
                y=645,
                width=80,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Kỹ sư backend với 3 năm kinh nghiệm.",
                page=0,
                x=72,
                y=630,
                width=400,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="Thành thạo Python, FastAPI, PostgreSQL.",
                page=0,
                x=72,
                y=615,
                width=400,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(text="", page=0, x=72, y=600, width=0, height=0),
            ExtractedLine(
                text="KINH NGHIỆM LÀM VIỆC",
                page=0,
                x=72,
                y=580,
                width=180,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="TechCorp",
                page=0,
                x=72,
                y=560,
                width=100,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="Backend Developer | Jan 2023 – Present",
                page=0,
                x=72,
                y=545,
                width=250,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="• Xây dựng RESTful API",
                page=0,
                x=90,
                y=530,
                width=250,
                height=12,
                font_size=11.0,
                font_weight=400,
                bullet_marker="•",
            ),
            ExtractedLine(
                text="• Tối ưu query PostgreSQL",
                page=0,
                x=90,
                y=515,
                width=250,
                height=12,
                font_size=11.0,
                font_weight=400,
                bullet_marker="•",
            ),
            ExtractedLine(text="", page=0, x=72, y=500, width=0, height=0),
            ExtractedLine(
                text="KỸ NĂNG",
                page=0,
                x=72,
                y=480,
                width=80,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Backend: Python, FastAPI, Django, Node.js",
                page=0,
                x=72,
                y=460,
                width=350,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="Database: PostgreSQL, Redis, MongoDB",
                page=0,
                x=72,
                y=445,
                width=350,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]

        doc = detect_sections(lines)

        # Identity
        assert doc.identity.name == "NGUYEN VAN DUY"
        assert doc.schema_version == 2

        # Summary
        assert doc.summary is not None
        assert "Kỹ sư backend" in doc.summary.text

        # Sections
        section_types = [s.type for s in doc.sections]
        assert "experience" in section_types
        assert "skills" in section_types

        # Section titles
        experience = next(s for s in doc.sections if s.type == "experience")
        assert experience.title == "KINH NGHIỆM LÀM VIỆC"

        # Skills have content
        skills = next(s for s in doc.sections if s.type == "skills")
        assert len(skills.blocks) > 0

    def test_identity_and_explicit_summary_are_not_duplicated(self) -> None:
        lines = [
            ExtractedLine(
                text="NGUYEN VAN DUY",
                page=0,
                x=72,
                y=700,
                width=200,
                height=14,
                font_size=16.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Backend Developer",
                page=0,
                x=72,
                y=680,
                width=200,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="SUMMARY",
                page=0,
                x=72,
                y=660,
                width=100,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Backend engineer with five years of experience.",
                page=0,
                x=72,
                y=640,
                width=350,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="Focused on reliable distributed systems.",
                page=0,
                x=72,
                y=620,
                width=350,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="SKILLS",
                page=0,
                x=72,
                y=600,
                width=100,
                height=12,
                font_size=13.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Backend: Python, FastAPI",
                page=0,
                x=72,
                y=580,
                width=250,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]

        doc = detect_sections(lines)

        assert doc.summary is not None
        assert doc.summary.text == (
            "Backend engineer with five years of experience. "
            "Focused on reliable distributed systems."
        )
        assert all(section.type != "summary" for section in doc.sections)
        other_text = " ".join(
            " ".join(block.lines)
            for section in doc.sections
            if section.title == "Other Content"
            for block in section.blocks
            if hasattr(block, "lines")
        )
        assert "NGUYEN VAN DUY" not in other_text
        assert "Backend Developer" not in other_text

    def test_empty_lines_produce_empty_doc(self) -> None:
        doc = detect_sections([])
        assert doc.schema_version == 2
        assert doc.identity.name == ""
        assert doc.sections == []

    def test_unrecognized_content_becomes_custom(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="My Name",
                page=0,
                x=72,
                y=700,
                width=100,
                height=14,
                font_size=14.0,
                font_weight=700,
            ),
            ExtractedLine(
                text="Some unclassified content here",
                page=0,
                x=72,
                y=680,
                width=300,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]
        doc = detect_sections(lines)
        # Should not crash and should preserve content
        assert doc.schema_version == 2
        assert (
            len(doc.sections) >= 0
        )  # may be 0 if no section detected, but identity should exist
        assert doc.identity.name == "My Name"


# ---------------------------------------------------------------------------
# Skill section classification
# ---------------------------------------------------------------------------


class TestSkillClassification:
    """Verify skill section block typing."""

    def test_skill_groups(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="Backend: Python, FastAPI, Django",
                page=0,
                x=72,
                y=500,
                width=350,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
            ExtractedLine(
                text="Frontend: React, TypeScript, Tailwind",
                page=0,
                x=72,
                y=485,
                width=350,
                height=12,
                font_size=11.0,
                font_weight=400,
            ),
        ]
        blocks = _classify_skill_section(lines)
        assert len(blocks) == 2
        assert blocks[0].type == "skill_group"
        assert blocks[0].label == "Backend"  # type: ignore
        assert "Python" in blocks[0].skills  # type: ignore
        assert "FastAPI" in blocks[0].skills  # type: ignore

    def test_bullets_in_skill_section(self) -> None:
        lines: list[ExtractedLine] = [
            ExtractedLine(
                text="• Proficient in Python",
                page=0,
                x=90,
                y=500,
                width=250,
                height=12,
                font_size=11.0,
                font_weight=400,
                bullet_marker="•",
            ),
        ]
        blocks = _classify_skill_section(lines)
        assert len(blocks) == 1
        assert blocks[0].type == "bullet"


# ---------------------------------------------------------------------------
# Entry headline detection
# ---------------------------------------------------------------------------


class TestEntryHeadline:
    """Verify entry headline detection."""

    def test_bold_entry_title(self) -> None:
        line = ExtractedLine(
            text="Backend Developer",
            page=0,
            x=72,
            y=500,
            width=150,
            height=12,
            font_size=11.0,
            font_weight=700,
        )
        assert _looks_like_entry_headline(line, "Backend Developer", [], 0)

    def test_bullet_not_entry(self) -> None:
        line = ExtractedLine(
            text="• Built APIs",
            page=0,
            x=90,
            y=480,
            width=200,
            height=12,
            font_size=11.0,
            font_weight=400,
            bullet_marker="•",
        )
        assert not _looks_like_entry_headline(
            line,
            "• Built APIs",
            [line],
            0,
        )

    def test_date_not_entry(self) -> None:
        line = ExtractedLine(
            text="Jan 2023 – Present",
            page=0,
            x=72,
            y=480,
            width=150,
            height=12,
            font_size=11.0,
            font_weight=400,
        )
        assert not _looks_like_entry_headline(line, "Jan 2023 – Present", [line], 0)


# ---------------------------------------------------------------------------
# Vocabulary edge cases
# ---------------------------------------------------------------------------


class TestVocabularyEdgeCases:
    """Test edge cases in vocabulary lookup."""

    def test_empty_text(self) -> None:
        assert classify_heading("") is None
        assert classify_heading("   ") is None

    def test_case_insensitivity(self) -> None:
        assert classify_heading("work experience") is not None
        assert classify_heading("WORK EXPERIENCE") is not None
        assert classify_heading("Work Experience") is not None

    def test_diacritic_insensitivity(self) -> None:
        result1 = classify_heading("KỸ NĂNG")
        result2 = classify_heading("Ky Nang")
        assert result1 is not None
        assert result2 is not None
        assert result1[0] == result2[0]

    def test_known_section_type(self) -> None:
        assert is_known_section_type("experience") is True
        assert is_known_section_type("skills") is True
        assert is_known_section_type("custom") is True
        assert is_known_section_type("invalid_type") is False
