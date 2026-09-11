"""Phase 3 — Layout-aware extraction tests.

Covers the four steps:
  Step 3.1  Preserve extraction metadata (ExtractedLine model)
  Step 3.2  Normalize extraction noise
  Step 3.3  Detect reading order (columns, sorting)
  Step 3.4  Detect physical line continuation

Run with:
    cd backend && pytest tests/test_layout_extraction.py -v
"""

from app.models.cv_document_v2 import (
    unwrap_google_redirect_url,
    unwrap_google_urls_in_text,
)
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.services.layout_extraction import (
    ExtractedLine,
    _cluster_coordinate_ranges,
    _cluster_coordinates,
    _collapse_whitespace,
    _detect_page_marker,
    _group_words_into_lines,
    _is_job_metadata_line,
    _is_known_section_heading,
    _looks_like_company_boundary,
    _looks_like_date,
    _looks_like_role_boundary,
    _mark_layout_artifacts,
    _normalize_bullet,
    _remove_soft_hyphens,
    _remove_zero_width_spaces,
    _replace_nbsp,
    _should_append_to_bullet,
    assign_columns,
    extract_text_from_layout,
    layout_extract_pdf,
    normalize_line,
    read_blocks_in_order,
    should_join_lines,
    sort_by_reading_order,
)

# ---------------------------------------------------------------------------
# Step 3.1: ExtractedLine model
# ---------------------------------------------------------------------------


class TestExtractedLineModel:
    """Verify the ExtractedLine dataclass captures all required metadata."""

    def test_minimal_construction(self) -> None:
        line = ExtractedLine(text="Hello", page=0, x=72, y=700, width=100, height=12)
        assert line.text == "Hello"
        assert line.page == 0
        assert line.font_size is None
        assert line.font_weight is None
        assert line.bullet_marker is None
        assert line.normalized_text == ""
        assert line.column_id is None
        assert line.joined_to_prev is False
        assert line.is_page_break_marker is False

    def test_full_construction(self) -> None:
        line = ExtractedLine(
            text="• Built APIs",
            page=0,
            x=72,
            y=650,
            width=200,
            height=14,
            font_size=12.0,
            font_weight=400,
            bullet_marker="•",
        )
        assert line.bullet_marker == "•"
        assert line.font_size == 12.0
        assert line.font_weight == 400

    def test_repr(self) -> None:
        line = ExtractedLine(
            text="Test content", page=1, x=50, y=300, width=400, height=14
        )
        assert "ExtractedLine(page=1" in repr(line)
        assert "x=50" in repr(line)
        assert "'Test content'" in repr(line)


# ---------------------------------------------------------------------------
# Step 3.2: Normalization
# ---------------------------------------------------------------------------


class TestBulletNormalization:
    """Unicode bullet variants must be normalised to canonical BULLET (•)."""

    def test_bullet_dot(self) -> None:
        text, marker = _normalize_bullet("• Built APIs")
        assert text == "• Built APIs"
        assert marker == "•"

    def test_bullet_circle(self) -> None:
        text, marker = _normalize_bullet("● Built APIs")
        assert text == "• Built APIs"
        assert marker == "●"

    def test_triangular_bullet(self) -> None:
        text, marker = _normalize_bullet("‣ Built APIs")
        assert text == "• Built APIs"
        assert marker == "‣"

    def test_square_bullet(self) -> None:
        text, marker = _normalize_bullet("▪ Built APIs")
        assert text == "• Built APIs"
        assert marker == "▪"

    def test_white_bullet(self) -> None:
        text, marker = _normalize_bullet("◦ Built APIs")
        assert text == "• Built APIs"
        assert marker == "◦"

    def test_dash_bullet(self) -> None:
        """Dash/hyphen bullets must be detected (no_bullet fix)."""
        text, marker = _normalize_bullet("- Built APIs")
        assert text == "• Built APIs"
        assert marker == "-"

    def test_hyphen_bullet(self) -> None:
        text, marker = _normalize_bullet("-Built APIs")
        assert "• Built APIs" in text
        assert marker == "-"

    def test_no_bullet(self) -> None:
        text, marker = _normalize_bullet("Regular paragraph text")
        assert text == "Regular paragraph text"
        assert marker is None

    def test_bullet_with_leading_spaces(self) -> None:
        """Bullet normalization removes extraction-only indentation."""
        text, _marker = _normalize_bullet("  • Built APIs")
        assert text.startswith("•")


class TestWhitespaceNormalisation:
    def test_collapse_repeated_spaces(self) -> None:
        assert _collapse_whitespace("Hello    world") == "Hello world"

    def test_collapse_tabs(self) -> None:
        assert _collapse_whitespace("Hello\tworld") == "Hello world"

    def test_strip(self) -> None:
        assert _collapse_whitespace("  Hello world  ") == "Hello world"


class TestSoftHyphenRemoval:
    def test_removes_soft_hyphen(self) -> None:
        result = _remove_soft_hyphens("re­sumé")
        assert "­" not in result
        assert result == "resumé"

    def test_no_hyphen_unchanged(self) -> None:
        assert _remove_soft_hyphens("hello world") == "hello world"


class TestZeroWidthSpaceRemoval:
    def test_removes_zws(self) -> None:
        result = _remove_zero_width_spaces("hello\u200bworld")
        assert "\u200b" not in result

    def test_no_zws_unchanged(self) -> None:
        assert _remove_zero_width_spaces("hello world") == "hello world"


class TestNBSPReplacement:
    def test_replaces_nbsp(self) -> None:
        assert _replace_nbsp("hello world") == "hello world"


class TestPageMarkerDetection:
    def test_simple_page_marker(self) -> None:
        assert _detect_page_marker("--- PAGE 2 ---") is True

    def test_page_with_number(self) -> None:
        assert _detect_page_marker("PAGE 3") is True

    def test_equally_spaced_page(self) -> None:
        assert _detect_page_marker("== PAGE 1 ==") is True

    def test_not_a_page_marker(self) -> None:
        assert _detect_page_marker("Page count is 5") is False

    def test_body_number_is_not_a_page_marker(self) -> None:
        assert _detect_page_marker("2") is False

    def test_normal_text_not_marker(self) -> None:
        assert _detect_page_marker("Built scalable APIs") is False


class TestFullLineNormalization:
    def test_bullet_normalised(self) -> None:
        line = ExtractedLine(
            text="● Built APIs", page=0, x=72, y=650, width=100, height=12
        )
        normalize_line(line)
        assert line.normalized_text == "• Built APIs"
        assert line.bullet_marker == "●"

    def test_dash_bullet_normalised(self) -> None:
        line = ExtractedLine(
            text="- Built APIs", page=0, x=72, y=650, width=100, height=12
        )
        normalize_line(line)
        assert "• Built APIs" in line.normalized_text
        assert line.bullet_marker == "-"

    def test_page_marker_detected(self) -> None:
        line = ExtractedLine(
            text="--- PAGE 2 ---", page=1, x=0, y=0, width=612, height=12
        )
        normalize_line(line)
        assert line.is_page_break_marker is True

    def test_soft_hyphen_removed(self) -> None:
        line = ExtractedLine(text="re­sumeé", page=0, x=72, y=650, width=100, height=12)
        normalize_line(line)
        assert "­" not in line.normalized_text

    def test_whitespace_collapsed(self) -> None:
        line = ExtractedLine(
            text="Hello    world", page=0, x=72, y=650, width=100, height=12
        )
        normalize_line(line)
        assert line.normalized_text == "Hello world"


class TestLayoutArtifactNormalization:
    def test_repeated_margin_header_is_flagged(self) -> None:
        lines = [
            ExtractedLine(
                text="Jane Doe",
                page=0,
                x=72,
                y=20,
                width=100,
                height=12,
                page_height=792,
            ),
            ExtractedLine(
                text="Jane Doe",
                page=1,
                x=72,
                y=20,
                width=100,
                height=12,
                page_height=792,
            ),
        ]
        for line in lines:
            normalize_line(line)
        _mark_layout_artifacts(lines)
        assert all(line.is_layout_artifact for line in lines)

    def test_standalone_footer_page_number_is_flagged(self) -> None:
        line = ExtractedLine(
            text="2",
            page=1,
            x=300,
            y=770,
            width=10,
            height=12,
            page_height=792,
        )
        normalize_line(line)
        _mark_layout_artifacts([line])
        assert line.is_layout_artifact is True


class TestWordGrouping:
    def test_nearby_word_tops_share_a_physical_line(self) -> None:
        words = [
            {"text": "Backend", "x0": 72, "x1": 120, "top": 100.0},
            {"text": "Engineer", "x0": 130, "x1": 180, "top": 101.2},
            {"text": "Experience", "x0": 72, "x1": 140, "top": 130.0},
        ]
        groups = _group_words_into_lines(words)
        assert [[word["text"] for word in group] for group in groups] == [
            ["Backend", "Engineer"],
            ["Experience"],
        ]

    def test_multicolumn_same_y_words_are_split_across_gutter(self) -> None:
        # Multi-column layout with 3 Y bands establishing a stable vertical gutter around x=250
        words = [
            {"text": "CAREER", "x0": 50, "x1": 110, "top": 100.0},
            {"text": "OBJECTIVE", "x0": 115, "x1": 180, "top": 100.0},
            {"text": "PHAM", "x0": 350, "x1": 400, "top": 100.0},
            {"text": "THAO", "x0": 405, "x1": 450, "top": 100.0},
            {"text": "EDUCATION", "x0": 50, "x1": 140, "top": 140.0},
            {"text": "email@gmail.com", "x0": 350, "x1": 480, "top": 140.0},
            {"text": "EXPERIENCE", "x0": 50, "x1": 150, "top": 180.0},
            {"text": "+84123456789", "x0": 350, "x1": 460, "top": 180.0},
        ]
        groups = _group_words_into_lines(words, page_width=612.0)
        group_texts = [" ".join(w["text"] for w in g) for g in groups]
        assert "CAREER OBJECTIVE" in group_texts
        assert "PHAM THAO" in group_texts
        assert "EDUCATION" in group_texts
        assert "email@gmail.com" in group_texts
        assert "EXPERIENCE" in group_texts
        assert "+84123456789" in group_texts

    def test_single_column_title_with_right_aligned_date_not_split(self) -> None:
        # Single role title with right aligned date on a single band (not 3+ bands)
        words = [
            {"text": "Backend", "x0": 50, "x1": 110, "top": 100.0},
            {"text": "Engineer", "x0": 115, "x1": 170, "top": 100.0},
            {"text": "2024", "x0": 480, "x1": 510, "top": 100.0},
            {"text": "–", "x0": 515, "x1": 525, "top": 100.0},
            {"text": "Present", "x0": 530, "x1": 570, "top": 100.0},
            {"text": "Description", "x0": 50, "x1": 130, "top": 120.0},
            {"text": "line", "x0": 135, "x1": 160, "top": 120.0},
        ]
        groups = _group_words_into_lines(words, page_width=612.0)
        group_texts = [" ".join(w["text"] for w in g) for g in groups]
        assert "Backend Engineer 2024 – Present" in group_texts

    def test_full_width_heading_spanning_gutter_not_split(self) -> None:
        words = [
            {"text": "LeftCol", "x0": 50, "x1": 120, "top": 100.0},
            {"text": "RightCol", "x0": 350, "x1": 420, "top": 100.0},
            {"text": "LeftCol2", "x0": 50, "x1": 120, "top": 140.0},
            {"text": "RightCol2", "x0": 350, "x1": 420, "top": 140.0},
            {"text": "LeftCol3", "x0": 50, "x1": 120, "top": 180.0},
            {"text": "RightCol3", "x0": 350, "x1": 420, "top": 180.0},
            # Spanning heading right in the middle
            {"text": "SUMMARY", "x0": 50, "x1": 150, "top": 220.0},
            {"text": "OF", "x0": 155, "x1": 180, "top": 220.0},
            {
                "text": "QUALIFICATIONS",
                "x0": 185,
                "x1": 450,
                "top": 220.0,
            },  # spans across x=230 gutter
        ]
        groups = _group_words_into_lines(words, page_width=612.0)
        group_texts = [" ".join(w["text"] for w in g) for g in groups]
        assert "SUMMARY OF QUALIFICATIONS" in group_texts

    def test_three_column_skills_layout(self) -> None:
        words = [
            {"text": "Python", "x0": 50, "x1": 110, "top": 100.0},
            {"text": "Docker", "x0": 220, "x1": 280, "top": 100.0},
            {"text": "PostgreSQL", "x0": 400, "x1": 480, "top": 100.0},
            {"text": "FastAPI", "x0": 50, "x1": 110, "top": 120.0},
            {"text": "Kubernetes", "x0": 220, "x1": 300, "top": 120.0},
            {"text": "Redis", "x0": 400, "x1": 450, "top": 120.0},
            {"text": "TypeScript", "x0": 50, "x1": 130, "top": 140.0},
            {"text": "AWS", "x0": 220, "x1": 250, "top": 140.0},
            {"text": "Git", "x0": 400, "x1": 420, "top": 140.0},
        ]
        groups = _group_words_into_lines(words, page_width=612.0)
        group_texts = [" ".join(w["text"] for w in g) for g in groups]
        assert "Python" in group_texts
        assert "Docker" in group_texts
        assert "PostgreSQL" in group_texts


# ---------------------------------------------------------------------------
# Step 3.3: Column detection and reading order
# ---------------------------------------------------------------------------


class TestCoordinateClustering:
    def test_single_point(self) -> None:
        assert _cluster_coordinates([72], 15) == [(72, 72)]

    def test_close_points_merged(self) -> None:
        assert _cluster_coordinates([70, 72, 75, 80], 15) == [(70, 80)]

    def test_far_points_separate(self) -> None:
        result = _cluster_coordinates([72, 400], 15)
        assert len(result) == 2

    def test_multiple_clusters(self) -> None:
        result = _cluster_coordinates([72, 75, 80, 300, 305, 500], 15)
        assert len(result) == 3

    def test_empty(self) -> None:
        assert _cluster_coordinates([], 15) == []


class TestRangeClustering:
    def test_overlapping_merged(self) -> None:
        result = _cluster_coordinate_ranges([(70, 100), (90, 130)], 10)
        assert len(result) == 1
        assert result[0] == (70, 130)

    def test_separate_preserved(self) -> None:
        result = _cluster_coordinate_ranges([(70, 100), (400, 450)], 10)
        assert len(result) == 2

    def test_empty(self) -> None:
        assert _cluster_coordinate_ranges([], 10) == []


class TestColumnAssignment:
    def test_single_column_all_assigned(self) -> None:
        lines = [
            ExtractedLine(text="Line 1", page=0, x=72, y=700, width=400, height=12),
            ExtractedLine(text="Line 2", page=0, x=72, y=680, width=400, height=12),
        ]
        result = assign_columns(lines, 612)
        for line in result:
            assert line.column_id == "main"

    def test_two_column_detected(self) -> None:
        lines = [
            ExtractedLine(text="Left col", page=0, x=30, y=700, width=250, height=12),
            ExtractedLine(text="Right col", page=0, x=350, y=700, width=250, height=12),
        ]
        result = assign_columns(lines, 612)
        column_ids = {line.column_id for line in result}
        assert len(column_ids) == 2  # Two distinct columns

    def test_empty_lines(self) -> None:
        assert assign_columns([], 612) == []


class TestReadingOrderSorting:
    def test_single_column_sorted_by_y(self) -> None:
        lines = [
            ExtractedLine(text="bottom", page=0, x=72, y=700, width=400, height=12),
            ExtractedLine(text="top", page=0, x=72, y=300, width=400, height=12),
        ]
        result = sort_by_reading_order(lines)
        assert result[0].text == "top"
        assert result[1].text == "bottom"

    def test_multi_column_left_first(self) -> None:
        lines = [
            ExtractedLine(text="right", page=0, x=400, y=500, width=200, height=12),
            ExtractedLine(text="left", page=0, x=50, y=500, width=200, height=12),
        ]
        lines[0].column_id = "col-1"
        lines[1].column_id = "col-0"
        result = sort_by_reading_order(lines)
        assert result[0].text == "left"
        assert result[1].text == "right"
        assert len(result) == 2

    def test_centered_heading_does_not_create_false_column(self) -> None:
        lines = [
            ExtractedLine(text="JANE DOE", page=0, x=240, y=30, width=100, height=16),
            ExtractedLine(text="Summary", page=0, x=72, y=80, width=400, height=12),
        ]
        assign_columns(lines, 612)
        result = sort_by_reading_order(lines)
        assert [line.text for line in result] == ["JANE DOE", "Summary"]
        assert {line.column_id for line in result} == {"main"}


# ---------------------------------------------------------------------------
# Step 3.4: Physical line continuation detection
# ---------------------------------------------------------------------------


class TestSectionHeadingDetection:
    def test_skills_is_heading(self) -> None:
        assert _is_known_section_heading("SKILLS") is True

    def test_experience_is_heading(self) -> None:
        assert _is_known_section_heading("WORK EXPERIENCE") is True

    def test_managerial_not_heading(self) -> None:
        assert _is_known_section_heading("managerial interview scenarios") is False

    def test_bootstrap_not_heading(self) -> None:
        assert _is_known_section_heading("Bootstrap, CSS-in-JS, Sass/Less") is False

    def test_retrieval_not_heading(self) -> None:
        assert _is_known_section_heading("Retrieval for Video Understanding") is False

    def test_proceedings_not_heading(self) -> None:
        assert _is_known_section_heading("Proceedings of IEEE/CVF CVPR") is False

    def test_with_colon(self) -> None:
        assert _is_known_section_heading("Skills:") is True

    def test_vietnamese_heading(self) -> None:
        assert _is_known_section_heading("KỸ NĂNG") is True
        assert _is_known_section_heading("KINH NGHIỆM LÀM VIỆC") is True


class TestDateDetection:
    def test_year_range(self) -> None:
        assert _looks_like_date("2020 – 2023") is True

    def test_year_with_present(self) -> None:
        assert _looks_like_date("Jan 2022 – Present") is True

    def test_month_year(self) -> None:
        assert _looks_like_date("September 2021 – Present") is True

    def test_not_a_date(self) -> None:
        assert _looks_like_date("Built scalable APIs") is False

    def test_not_a_date_numbers_only(self) -> None:
        assert _looks_like_date("100 requests") is False


class TestRoleBoundaryDetection:
    def test_engineer_detected(self) -> None:
        assert _looks_like_role_boundary("Backend Engineer") is True

    def test_developer_detected(self) -> None:
        assert _looks_like_role_boundary("Software Developer") is True

    def test_manager_detected(self) -> None:
        assert _looks_like_role_boundary("Manager") is True

    def test_managerial_not_detected(self) -> None:
        """'managerial' must NOT match 'manager' role keyword."""
        assert _looks_like_role_boundary("managerial interview scenarios") is False

    def test_managerial_word_boundary(self) -> None:
        assert _looks_like_role_boundary("managerial") is False

    def test_senior_detected(self) -> None:
        assert _looks_like_role_boundary("Senior Software Engineer") is True

    def test_intern_detected(self) -> None:
        assert _looks_like_role_boundary("Intern Software Engineer") is True

    def test_not_a_role(self) -> None:
        assert _looks_like_role_boundary("Built the backend API") is False


class TestCompanyBoundaryDetection:
    def test_company_detected(self) -> None:
        assert _looks_like_company_boundary("TechCorp Company") is True

    def test_university_detected(self) -> None:
        assert _looks_like_company_boundary("FPT University") is True

    def test_vietnamese_company_detected(self) -> None:
        assert _looks_like_company_boundary("Đại học Bách Khoa") is True

    def test_not_a_company(self) -> None:
        assert _looks_like_company_boundary("Built the backend API") is False


class TestBulletAppending:
    def test_wrapped_skill_continuation(self) -> None:
        assert (
            _should_append_to_bullet(
                "• Styling: Tailwind CSS, Styled Components, Material UI,",
                "  Bootstrap, CSS-in-JS, Sass/Less",
            )
            is True
        )

    def test_no_terminal_punctuation_joins(self) -> None:
        assert (
            _should_append_to_bullet(
                "• Developed RESTful APIs for banking",
                "  applications with OAuth 2.0",
            )
            is True
        )

    def test_terminal_punctuation_stops_joining(self) -> None:
        assert (
            _should_append_to_bullet(
                "• Built the API.",
                "Then deployed it.",
            )
            is False
        )

    def test_new_bullet_stops_joining(self) -> None:
        assert (
            _should_append_to_bullet(
                "• Built the API",
                "• Deployed it",
            )
            is False
        )

    def test_job_metadata_stops_joining(self) -> None:
        assert (
            _should_append_to_bullet(
                "• Developed the backend",
                "Backend Developer | Jan 2023 – Present",
            )
            is False
        )

    def test_non_bullet_prev_not_joined(self) -> None:
        assert (
            _should_append_to_bullet(
                "Regular paragraph text",
                "continuation line",
            )
            is False
        )


class TestJobMetadataDetection:
    def test_date_line_is_metadata(self) -> None:
        assert _is_job_metadata_line("Jan 2023 – Present") is True

    def test_lowercase_is_not_metadata(self) -> None:
        assert _is_job_metadata_line("bootstrap, css-in-js") is False

    def test_role_line_is_metadata(self) -> None:
        assert _is_job_metadata_line("Backend Developer") is True

    def test_company_line_is_metadata(self) -> None:
        assert _is_job_metadata_line("TechCorp Company") is True

    def test_normal_text_not_metadata(self) -> None:
        assert _is_job_metadata_line("Built scalable APIs") is False


class TestLineJoining:
    def test_bullet_continuation_joined(self) -> None:
        prev = ExtractedLine(
            text="• Built scalable APIs",
            page=0,
            x=72,
            y=650,
            width=200,
            height=14,
            bullet_marker="•",
        )
        prev.normalized_text = "• Built scalable APIs"
        curr = ExtractedLine(
            text="  with sub-200ms latency",
            page=0,
            x=72,
            y=670,
            width=200,
            height=14,
        )
        curr.normalized_text = "with sub-200ms latency"
        assert should_join_lines(prev, curr, prev_is_bullet=True) is True

    def test_page_gap_too_large(self) -> None:
        prev = ExtractedLine(
            text="Line 1",
            page=0,
            x=72,
            y=650,
            width=200,
            height=14,
        )
        prev.normalized_text = "Line 1"
        curr = ExtractedLine(
            text="Line 2",
            page=5,
            x=72,
            y=100,
            width=200,
            height=14,
        )
        curr.normalized_text = "Line 2"
        assert should_join_lines(prev, curr) is False

    def test_different_columns_not_joined(self) -> None:
        prev = ExtractedLine(
            text="Left col",
            page=0,
            x=30,
            y=650,
            width=200,
            height=14,
        )
        prev.column_id = "col-0"
        prev.normalized_text = "Left col"
        curr = ExtractedLine(
            text="Right col",
            page=0,
            x=400,
            y=650,
            width=200,
            height=14,
        )
        curr.column_id = "col-1"
        curr.normalized_text = "Right col"
        assert should_join_lines(prev, curr) is False

    def test_page_break_marker_not_joined(self) -> None:
        prev = ExtractedLine(
            text="• Built APIs",
            page=0,
            x=72,
            y=650,
            width=200,
            height=14,
            bullet_marker="•",
        )
        prev.normalized_text = "• Built APIs"
        curr = ExtractedLine(
            text="--- PAGE 2 ---",
            page=1,
            x=0,
            y=100,
            width=612,
            height=12,
        )
        curr.is_page_break_marker = True
        curr.normalized_text = "--- PAGE 2 ---"
        assert should_join_lines(prev, curr) is False

    def test_section_heading_not_joined(self) -> None:
        prev = ExtractedLine(
            text="Previous content",
            page=0,
            x=72,
            y=650,
            width=200,
            height=14,
        )
        prev.normalized_text = "Previous content"
        curr = ExtractedLine(
            text="SKILLS",
            page=0,
            x=72,
            y=640,
            width=100,
            height=14,
        )
        curr.normalized_text = "SKILLS"
        assert should_join_lines(prev, curr) is False

    def test_terminal_punctuation_stops_join(self) -> None:
        prev = ExtractedLine(
            text="Built the API.",
            page=0,
            x=72,
            y=650,
            width=200,
            height=14,
        )
        prev.normalized_text = "Built the API."
        curr = ExtractedLine(
            text="Then deployed it.",
            page=0,
            x=72,
            y=640,
            width=200,
            height=14,
        )
        curr.normalized_text = "Then deployed it."
        assert should_join_lines(prev, curr) is False

    def test_date_boundary_not_joined(self) -> None:
        prev = ExtractedLine(
            text="Previous content",
            page=0,
            x=72,
            y=650,
            width=200,
            height=14,
        )
        prev.normalized_text = "Previous content"
        curr = ExtractedLine(
            text="Jan 2023 – Present",
            page=0,
            x=72,
            y=640,
            width=200,
            height=14,
        )
        curr.normalized_text = "Jan 2023 – Present"
        assert should_join_lines(prev, curr) is False

    def test_large_x_gap_not_joined(self) -> None:
        prev = ExtractedLine(
            text="Left content",
            page=0,
            x=30,
            y=650,
            width=200,
            height=14,
        )
        prev.normalized_text = "Left content"
        curr = ExtractedLine(
            text="Right content",
            page=0,
            x=500,
            y=640,
            width=200,
            height=14,
        )
        curr.normalized_text = "Right content"
        assert should_join_lines(prev, curr) is False

    def test_consecutive_page_not_joined_by_default(self) -> None:
        """Lines on consecutive pages are allowed for continuation
        (cross-page bullet support).
        """
        prev = ExtractedLine(
            text="• Built scalable",
            page=0,
            x=72,
            y=740,
            width=200,
            height=14,
            bullet_marker="•",
            page_height=792,
        )
        prev.normalized_text = "• Built scalable"
        curr = ExtractedLine(
            text="  with FastAPI",
            page=1,
            x=72,
            y=60,
            width=200,
            height=14,
            page_height=792,
        )
        curr.normalized_text = "with FastAPI"
        # This should be joinable across pages when signals agree
        assert should_join_lines(prev, curr) is True

    def test_non_bullet_lowercase_continuation_is_joined(self) -> None:
        prev = ExtractedLine(
            text="Built an event-driven",
            page=0,
            x=72,
            y=100,
            width=200,
            height=12,
        )
        prev.normalized_text = prev.text
        curr = ExtractedLine(
            text="architecture for payments",
            page=0,
            x=72,
            y=114,
            width=200,
            height=12,
        )
        curr.normalized_text = curr.text
        assert should_join_lines(prev, curr) is True


class TestExtractTextFromLayout:
    def test_single_line(self) -> None:
        lines = [ExtractedLine(text="Hello", page=0, x=0, y=0, width=50, height=12)]
        assert extract_text_from_layout(lines) == "Hello"

    def test_multiple_lines_with_newlines(self) -> None:
        lines = [
            ExtractedLine(text="Line 1", page=0, x=0, y=0, width=50, height=12),
            ExtractedLine(text="Line 2", page=0, x=0, y=14, width=50, height=12),
        ]
        result = extract_text_from_layout(lines)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_joined_lines_concatenated(self) -> None:
        lines = [
            ExtractedLine(text="Part 1", page=0, x=0, y=0, width=50, height=12),
            ExtractedLine(text="Part 2", page=0, x=0, y=14, width=50, height=12),
        ]
        lines[1].joined_to_prev = True
        lines[1].normalized_text = "Part 2"
        lines[0].normalized_text = "Part 1"
        result = extract_text_from_layout(lines)
        assert "Part 1 Part 2" in result

    def test_page_break_marker_inserted(self) -> None:
        lines = [
            ExtractedLine(text="Page 1 content", page=0, x=0, y=0, width=50, height=12),
            ExtractedLine(text="PAGE 2", page=1, x=0, y=100, width=50, height=12),
        ]
        lines[1].is_page_break_marker = True
        result = extract_text_from_layout(lines)
        assert "PAGE 2" not in result

    def test_joined_word_break_removes_hyphen(self) -> None:
        lines = [
            ExtractedLine(text="inter-", page=0, x=0, y=0, width=50, height=12),
            ExtractedLine(text="national", page=0, x=0, y=14, width=50, height=12),
        ]
        lines[1].joined_to_prev = True
        assert extract_text_from_layout(lines) == "international"


# ---------------------------------------------------------------------------
# Integration: full pipeline smoke test with a simple PDF
# ---------------------------------------------------------------------------


class _FakePage:
    width = 612
    height = 792

    def __init__(self, texts: list[str]):
        self.texts = texts

    def extract_words(self, **kwargs):
        assert kwargs["extra_attrs"] == ["fontname", "size"]
        return [
            {
                "text": text,
                "x0": 72,
                "x1": 72 + len(text) * 6,
                "top": 80 + index * 20,
                "bottom": 92 + index * 20,
                "fontname": "Helvetica",
                "size": 12,
            }
            for index, text in enumerate(self.texts)
        ]


class _FakePdf:
    def __init__(self, texts: list[str]):
        self.pages = [_FakePage(texts)]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _make_minimal_pdf(text_lines: list[str]) -> bytes:
    """Build a dependency-free PDF containing simple Helvetica text."""
    commands = ["BT /F1 12 Tf 72 720 Td"]
    for index, text in enumerate(text_lines):
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("0 -18 Td")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    content = " ".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, pdf_object in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(pdf_object + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode(),
    )
    return bytes(pdf)


class TestLayoutExtractionIntegration:
    """Exercise the pipeline against pdfplumber's word-result contract."""

    def _extract(self, monkeypatch, texts: list[str]) -> list[ExtractedLine]:
        monkeypatch.setattr(
            "app.services.layout_extraction.pdfplumber.open",
            lambda _stream: _FakePdf(texts),
        )
        return layout_extract_pdf(b"pdf bytes are intercepted")

    def test_simple_single_column(self, monkeypatch) -> None:
        lines = self._extract(
            monkeypatch,
            ["John Doe", "Software Engineer", "EXPERIENCE", "Built APIs"],
        )
        assert len(lines) > 0
        column_ids = {line.column_id for line in lines}
        assert column_ids == {"main"}
        for line in lines:
            assert line.normalized_text

    def test_preserves_bullet_markers(self, monkeypatch) -> None:
        lines = self._extract(
            monkeypatch,
            ["EXPERIENCE", "• Built APIs", "• Deployed services"],
        )
        bullet_lines = [line for line in lines if line.bullet_marker]
        assert len(bullet_lines) == 2

    def test_real_pdf_words_are_not_fragmented(self) -> None:
        expected = ["John Doe", "Software Engineer", "EXPERIENCE", "Built APIs"]
        lines = layout_extract_pdf(_make_minimal_pdf(expected))
        assert [line.text for line in lines] == expected
        assert all(line.width > 0 and line.height > 0 for line in lines)


# ---------------------------------------------------------------------------
# ``read_blocks_in_order`` — column-major reading order for ``RawBlock``
# ---------------------------------------------------------------------------


def _block(
    block_id: str,
    text: str,
    *,
    x: float,
    y: float,
    width: float = 100.0,
    height: float = 12.0,
) -> RawBlock:
    return RawBlock(
        block_id=block_id,
        page=1,
        text=text,
        bbox=(x, y, x + width, y + height),
        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        reading_order=0,
    )


def test_read_blocks_in_order_single_column_keeps_legacy_sort() -> None:
    """Single-column page: every block stays ``column_id is None`` and the
    output equals the legacy ``(y, x)`` sort.
    """
    blocks = [
        _block("a", "Header", x=40, y=80),
        _block("b", "First", x=40, y=120),
        _block("c", "Second", x=40, y=140),
        _block("d", "Third", x=40, y=160),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    assert [b.block_id for b in ordered] == ["a", "b", "c", "d"]
    assert all(b.column_id is None for b in ordered)


def test_read_blocks_in_order_two_columns_emits_left_then_right() -> None:
    """Two-column page with a clear gutter: left column emitted top-to-bottom
    first, then right column top-to-bottom. Spanning header stays at top.
    """
    blocks = [
        _block("hdr", "SKILLS", x=30, y=80, width=552),
        _block("cv", "Computer Vision", x=39, y=120),
        _block("prog", "Programming", x=316, y=120),
        _block("ocr", "Deep models in OCR", x=39, y=140),
        _block("pt", "Pytorch, OpenCV", x=316, y=140),
        _block("det", "Detection, Segmentation", x=39, y=160),
        _block("trt", "TensorRT", x=316, y=160),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    assert [b.block_id for b in ordered] == [
        "hdr",
        "cv",
        "ocr",
        "det",
        "prog",
        "pt",
        "trt",
    ]
    # Header sits at the top of column 1 because column detection operates
    # on bbox geometry only; heading detection is the partition layer's
    # responsibility (via ``classify_heading``).
    assert ordered[0].column_id == 1
    assert {b.column_id for b in ordered[1:]} == {1, 2}


def test_read_blocks_in_order_three_columns_each_top_to_bottom() -> None:
    """Three-column page: each column reads independently, emitted
    left-to-right.
    """
    blocks = [
        _block("hdr", "SKILLS", x=30, y=80, width=552),
        _block("a1", "A-One", x=39, y=120),
        _block("b1", "B-One", x=216, y=120),
        _block("c1", "C-One", x=393, y=120),
        _block("a2", "A-Two", x=39, y=140),
        _block("b2", "B-Two", x=216, y=140),
        _block("c2", "C-Two", x=393, y=140),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    assert [b.block_id for b in ordered] == [
        "hdr",
        "a1",
        "a2",
        "b1",
        "b2",
        "c1",
        "c2",
    ]
    assert [b.column_id for b in ordered[1:]] == [1, 1, 2, 2, 3, 3]


def test_read_blocks_in_order_spanning_block_at_y_mid() -> None:
    """A wide block placed mid-page (e.g. an EXPERIENCE heading inside a
    two-column page) is assigned to column 1 (the closest centroid) and
    emitted at its Y-position within that column. Heading detection is
    the partition layer's responsibility (``classify_heading``); this
    routine only assigns column membership.
    """
    blocks = [
        _block("cv", "Computer Vision", x=39, y=120),
        _block("prog", "Programming", x=316, y=120),
        _block("hdr_exp", "EXPERIENCE", x=30, y=200, width=552),
        _block("e1", "Engineer", x=39, y=240),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    assert [b.block_id for b in ordered] == ["cv", "hdr_exp", "e1", "prog"]


def test_read_blocks_in_order_sub_threshold_gap_treated_as_single_column() -> None:
    """Two x_min clusters separated by less than the dynamic threshold are
    treated as a single column (no column_id assigned).
    """
    blocks = [
        _block("a", "Header", x=40, y=80, width=120),
        _block("b", "Body", x=170, y=120, width=120),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=4000, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    assert [b.block_id for b in ordered] == ["a", "b"]
    assert all(b.column_id is None for b in ordered)


def test_read_blocks_in_order_does_not_treat_wide_bullet_as_spanning() -> None:
    """A bullet line that happens to be visually wide (e.g. wrapping across
    both columns) is NOT a heading and must not be hoisted to the top.
    """
    blocks = [
        _block("cv", "Computer Vision", x=39, y=120),
        _block("prog", "Programming", x=316, y=120),
        _block("bullet", "– Shipped production features.", x=51, y=140, width=400),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    assert [b.block_id for b in ordered] == ["cv", "bullet", "prog"]
    assert ordered[1].column_id == 1
    assert ordered[2].column_id == 2


def test_read_blocks_in_order_property_single_column_matches_legacy_sort() -> None:
    """Property: for any single-column page, ``read_blocks_in_order`` output
    equals the legacy ``(y, x)`` sort. Catches accidental row-major regression.
    """
    blocks = [
        _block("b1", "alpha", x=42, y=110),
        _block("b2", "beta", x=42, y=160),
        _block("b3", "gamma", x=42, y=130),
        _block("b4", "delta", x=42, y=200),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)
    legacy = sorted(blocks, key=lambda block: (block.bbox[1], block.bbox[0]))

    assert [b.block_id for b in ordered] == [b.block_id for b in legacy]


def test_read_blocks_in_order_merges_subcolumn_indentation() -> None:
    """Regression for vinh.pdf page 3: skill values are indented ~36pt
    under their category labels (x≈38 → x≈75). The 36pt gap exceeds the
    base column threshold (~36pt) and would otherwise create a phantom
    third column. The merge step must collapse the indent into the
    surrounding column.
    """
    blocks = [
        _block("hdr", "SKILLS", x=27, y=80, width=540),
        _block("cv_lbl", "Computer Vision", x=39, y=110),
        _block("cv_v1", "Deep models in OCR", x=75, y=130),
        _block("cv_v2", "Detection, Segmentation", x=75, y=150),
        _block("eng_lbl", "English", x=39, y=200),
        _block("eng_v1", "VNU-EPT 280", x=75, y=220),
        _block("prog_lbl", "Programming", x=316, y=110),
        _block("prog_v1", "Pytorch, OpenCV", x=352, y=130),
        _block("prog_v2", "TensorRT", x=352, y=150),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=595, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    # Two real columns (left + right); the indent at x≈75 must not split
    # off as a third.
    column_ids = {b.column_id for b in ordered if b.column_id is not None}
    assert column_ids == {1, 2}
    # Left column labels (x=39) and their indented values (x=75) share
    # the same column_id.
    cv_lbl = next(b for b in ordered if b.block_id == "cv_lbl")
    cv_v1 = next(b for b in ordered if b.block_id == "cv_v1")
    assert cv_lbl.column_id == cv_v1.column_id
    # Right column labels (x=316) and indented values (x=352) share the
    # same column_id.
    prog_lbl = next(b for b in ordered if b.block_id == "prog_lbl")
    prog_v1 = next(b for b in ordered if b.block_id == "prog_v1")
    assert prog_lbl.column_id == prog_v1.column_id


def test_read_blocks_in_order_keeps_real_narrow_gutter() -> None:
    """The merge step must NOT collapse a real (narrow-but-valid) two-column
    gutter. A standard 30pt gutter on a US-Letter page is the minimum
    legitimate column boundary.
    """
    blocks = [
        _block("a1", "Left One", x=40, y=100),
        _block("b1", "Right One", x=300, y=100),
        _block("a2", "Left Two", x=40, y=140),
        _block("b2", "Right Two", x=300, y=140),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ordered = read_blocks_in_order(raw)

    a1 = next(b for b in ordered if b.block_id == "a1")
    b1 = next(b for b in ordered if b.block_id == "b1")
    assert a1.column_id == 1
    assert b1.column_id == 2


class TestGoogleRedirectUnwrapping:
    def test_unwrap_standard_google_redirect(self) -> None:
        url = "https://www.google.com/url?q=https://linkedin.com/in/phvinh2000&sa=D&sntz=1&usg=AFQjCN..."
        unwrapped = unwrap_google_redirect_url(url)
        assert unwrapped == "https://linkedin.com/in/phvinh2000"

    def test_unwrap_encoded_google_redirect_with_nested_params(self) -> None:
        url = "https://www.google.com/url?q=https%3A%2F%2Fgithub.com%2Ffoo%3Ftab%3Dstars%26sort%3Ddesc&sa=D&ved=0ah"
        unwrapped = unwrap_google_redirect_url(url)
        assert unwrapped == "https://github.com/foo?tab=stars&sort=desc"

    def test_non_google_url_untouched(self) -> None:
        url = "https://example.com/some/path?param=1"
        assert unwrap_google_redirect_url(url) == url

    def test_unwrap_google_urls_in_free_text(self) -> None:
        text = "Profiles: https://www.google.com/url?q=https://linkedin.com/in/phvinh2000&sa=D and https://www.google.com/url?q=https://github.com/phvinh&sa=D."
        cleaned = unwrap_google_urls_in_text(text)
        assert (
            cleaned
            == "Profiles: https://linkedin.com/in/phvinh2000 and https://github.com/phvinh."
        )
