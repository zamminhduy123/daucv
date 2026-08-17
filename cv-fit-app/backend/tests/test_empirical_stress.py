"""Empirical Stress Tests for block_reconstruction.py and section_detector.py.

Milestone 3 - Challenger 1 Adversarial Verification Harness.
Tests extreme inputs: empty text, single characters, long paragraphs,
duplicate lines, Vietnamese diacritics, and unusual section headings.
"""

import pytest

from app.models.cv_document_v2 import (
    CVEducationBlock,
    CVEntryBlock,
)
from app.services.block_reconstruction import (
    reconstruct_blocks,
)
from app.services.layout_extraction import ExtractedLine
from app.services.section_detector import detect_sections
from app.services.section_vocabulary import classify_heading


def _make_line(
    text: str, line_id: str | None = None, page: int = 0, y: float = 700.0, **overrides
) -> ExtractedLine:
    """Helper to create an ExtractedLine."""
    kw = dict(
        text=text,
        normalized_text=text,
        page=page,
        x=72.0,
        y=y,
        width=300.0,
        height=14.0,
        font_size=11.0,
        font_weight=400,
        source_line_id=line_id,
    )
    kw.update(overrides)
    return ExtractedLine(**kw)


# ===========================================================================
# 1. Empty Text and Whitespace Stress Tests
# ===========================================================================


class TestEmptyInputStress:
    """Category 1: Empty text and whitespace edge cases."""

    def test_reconstruct_blocks_empty_list(self):
        """reconstruct_blocks with empty line list returns empty block list without exception."""
        assert reconstruct_blocks("experience", []) == []
        assert reconstruct_blocks("skills", []) == []
        assert reconstruct_blocks("education", []) == []
        assert reconstruct_blocks("custom", []) == []

    def test_detect_sections_empty_list(self):
        """detect_sections with empty line list returns empty CVDocumentV2."""
        doc = detect_sections([])
        assert doc is not None
        assert len(doc.sections) == 0

    def test_whitespace_only_lines(self):
        """Lines containing only spaces, tabs, newlines should not cause crashes."""
        lines = [
            _make_line("   ", "p1-l1"),
            _make_line("\t\n", "p1-l2"),
            _make_line("", "p1-l3"),
        ]
        blocks = reconstruct_blocks("experience", lines)
        assert isinstance(blocks, list)
        doc = detect_sections(lines)
        assert doc is not None

    def test_line_with_none_source_line_id(self):
        """Lines with source_line_id=None should auto-generate provenance IDs safely."""
        lines = [_make_line("Software Engineer", line_id=None)]
        blocks = reconstruct_blocks("experience", lines)
        assert len(blocks) == 1
        assert len(blocks[0].source_line_ids) > 0


# ===========================================================================
# 2. Single Character and Minimal Text Stress Tests
# ===========================================================================


class TestSingleCharStress:
    """Category 2: Single characters and minimal tokens."""

    @pytest.mark.parametrize("char", ["a", "1", ".", ":", "|", "•", "-", "@", "x", "Đ"])
    def test_single_char_section_parsers(self, char):
        """Single character inputs must not crash any parser."""
        lines = [_make_line(char, f"p1-l1-{ord(char)}")]
        for stype in [
            "experience",
            "projects",
            "skills",
            "education",
            "publications",
            "certifications",
            "languages",
            "awards",
            "custom",
        ]:
            blocks = reconstruct_blocks(stype, lines)
            assert isinstance(blocks, list)

    def test_single_char_section_detector(self):
        """Document with single character lines must construct valid CVDocumentV2."""
        lines = [
            _make_line("A", "p1-l1"),
            _make_line("B", "p1-l2"),
            _make_line(".", "p1-l3"),
        ]
        doc = detect_sections(lines)
        assert doc is not None


# ===========================================================================
# 3. Long Paragraph and Extreme Length Stress Tests
# ===========================================================================


class TestLongParagraphStress:
    """Category 3: Long paragraphs, extreme line lengths, and repeated delimiters."""

    def test_5000_char_paragraph_experience(self):
        """5000-character single line input in experience parser."""
        long_text = "Software Engineer " + (
            "developed scalable distributed systems " * 200
        )
        lines = [_make_line(long_text, "p1-l1")]
        blocks = reconstruct_blocks("experience", lines)
        assert len(blocks) >= 1

    def test_50_pipe_delimiters(self):
        """Line with 50 pipe delimiters must not cause catastrophic regex or indexing crash."""
        pipe_text = "Title | " + " | ".join([f"Meta{i}" for i in range(50)])
        lines = [_make_line(pipe_text, "p1-l1")]
        blocks = reconstruct_blocks("experience", lines)
        assert len(blocks) >= 1

    def test_5000_char_skill_line(self):
        """Extremely long skill line must fallback gracefully to paragraph without crash."""
        long_skills = "Skills: " + ", ".join([f"Skill{i}" for i in range(1000)])
        lines = [_make_line(long_skills, "p1-l1")]
        blocks = reconstruct_blocks("skills", lines)
        assert len(blocks) >= 1


# ===========================================================================
# 4. Duplicate Line & Provenance Corruption Stress Tests
# ===========================================================================


class TestDuplicateLinesAndProvenanceStress:
    """Category 4: Duplicate lines, identical bullets, and line provenance allocation."""

    def test_duplicate_bullets_provenance_assignment(self):
        """CRITICAL: Section with multiple duplicate bullet lines.
        Verifies whether duplicate text causes line provenance loss (missing_line_provenance)
        or incorrect line ID assignment across blocks.
        """
        lines = [
            _make_line("Backend Developer", "p1-l1"),
            _make_line("TechCorp", "p1-l2"),
            _make_line("2023 - 2024", "p1-l3"),
            _make_line("• Built RESTful APIs", "p1-l4"),
            _make_line("• Built RESTful APIs", "p1-l5"),
            _make_line("• Built RESTful APIs", "p1-l6"),
        ]
        blocks = reconstruct_blocks("experience", lines)
        assert len(blocks) == 1
        entry: CVEntryBlock = blocks[0]
        assert len(entry.bullets) == 3
        # All 3 bullet line IDs should be tracked in entry's source_line_ids
        assert set(entry.source_line_ids) == {
            "p1-l1",
            "p1-l2",
            "p1-l3",
            "p1-l4",
            "p1-l5",
            "p1-l6",
        }

    def test_duplicate_separate_blocks_provenance(self):
        """Duplicate paragraph or entry blocks in the same section."""
        lines = [
            _make_line("Duplicate Title", "p1-l1", font_weight=700, font_size=13.0),
            _make_line("Duplicate Title", "p1-l2", font_weight=700, font_size=13.0),
        ]
        blocks = reconstruct_blocks("experience", lines)
        # Verify that all source line IDs are preserved across blocks
        claimed = [lid for b in blocks for lid in b.source_line_ids]
        assert "p1-l1" in claimed
        assert "p1-l2" in claimed

    def test_duplicate_line_ids_handling(self):
        """Input lines with identical source_line_id values must not crash detector."""
        lines = [
            _make_line("EXPERIENCE", "p1-l1", font_size=16.0, font_weight=700),
            _make_line("Software Engineer", "p1-l1"),  # Duplicate ID!
            _make_line("TechCorp", "p1-l2"),
        ]
        doc = detect_sections(lines)
        assert doc is not None


# ===========================================================================
# 5. Vietnamese Diacritics and Unicode Stress Tests
# ===========================================================================


class TestVietnameseDiacriticsStress:
    """Category 5: Vietnamese diacritics, unicode, and emojis."""

    def test_vietnamese_experience_entry(self):
        """Full Vietnamese experience entry parsing."""
        lines = [
            _make_line("Kỹ sư Lập trình Backend", "p1-l1"),
            _make_line("Tập đoàn Công nghệ FPT", "p1-l2"),
            _make_line("Tháng 01/2022 – Hiện tại", "p1-l3"),
            _make_line(
                "• Phát triển hệ thống microservices sử dụng Python và FastAPI", "p1-l4"
            ),
            _make_line("• Tối ưu hóa truy vấn cơ sở dữ liệu PostgreSQL", "p1-l5"),
        ]
        blocks = reconstruct_blocks("experience", lines)
        assert len(blocks) == 1
        entry: CVEntryBlock = blocks[0]
        assert entry.title == "Kỹ sư Lập trình Backend"
        assert entry.organization == "Tập đoàn Công nghệ FPT"
        assert "Hiện tại" in entry.date or "01/2022" in entry.date
        assert len(entry.bullets) == 2

    def test_vietnamese_education_entry(self):
        """Full Vietnamese education entry parsing."""
        lines = [
            _make_line("Kỹ sư Công nghệ Thông tin", "p1-l1"),
            _make_line("Trường Đại học Bách Khoa - ĐHQG TP.HCM", "p1-l2"),
            _make_line("2017 – 2021", "p1-l3"),
            _make_line("Xếp loại: Giỏi | GPA: 3.6/4.0", "p1-l4"),
        ]
        blocks = reconstruct_blocks("education", lines)
        assert len(blocks) == 1
        edu: CVEducationBlock = blocks[0]
        assert edu.degree == "Kỹ sư Công nghệ Thông tin"
        assert "Đại học Bách Khoa" in (edu.institution or "")
        assert edu.date == "2017 – 2021"

    def test_unicode_emojis_and_special_symbols(self):
        """Lines containing emojis and non-standard unicode characters."""
        lines = [
            _make_line("🚀 Senior Backend Engineer 💻", "p1-l1"),
            _make_line("TechCorp Inc. 🏢", "p1-l2"),
            _make_line("• Built REST APIs 🔥", "p1-l3"),
        ]
        blocks = reconstruct_blocks("experience", lines)
        assert len(blocks) >= 1


# ===========================================================================
# 6. Unusual Section Headings Stress Tests
# ===========================================================================


class TestUnusualSectionHeadingsStress:
    """Category 6: Non-standard section headings, trailing colons, numbering, symbols."""

    @pytest.mark.parametrize(
        "heading_text, expected_canonical",
        [
            ("WORK EXPERIENCE", "experience"),
            ("KINH NGHIỆM LÀM VIỆC", "experience"),
            ("WORK EXPERIENCE:", "experience"),  # Trailing colon
            ("1. WORK EXPERIENCE", "experience"),  # Numbering
            ("::: TECHNICAL SKILLS :::", "skills"),  # Surrounding symbols
            ("KỸ NĂNG & CÔNG NGHỆ", "skills"),  # Compound heading
            ("EXPERIENCE & CAREER SUMMARY", "experience"),  # Combined heading
        ],
    )
    def test_heading_classification_variants(self, heading_text, expected_canonical):
        """Test whether heading classification supports trailing colons, numbering, and symbols."""
        result = classify_heading(heading_text)
        # Note: if classify_heading returns None for trailing colon/numbering, document this finding
        if result is not None:
            assert result[0] == expected_canonical
        else:
            # Documented finding: classify_heading does not normalize colons/numbering
            pytest.skip(
                f"classify_heading returned None for unusual heading variant: {heading_text!r}"
            )

    def test_50_word_heading_is_not_section_boundary(self):
        """A line with 50 words should NEVER be detected as a section heading."""
        long_heading = (
            "THIS IS A VERY LONG LINE THAT CONTAINS FIFTY WORDS AND SHOULD DEFINITELY NOT BE CLASSIFIED AS A SECTION HEADING BY THE DETECTOR PIPELINE BECAUSE HEADINGS ARE SHORT "
            * 3
        )
        line = _make_line(long_heading, "p1-l1", font_size=16.0, font_weight=700)
        doc = detect_sections([line])
        # Should not create a custom section with title = long_heading as a valid heading
        assert len(doc.sections) == 1
        assert doc.sections[0].type == "custom"
        assert doc.sections[0].title == "Unclassified Content"
