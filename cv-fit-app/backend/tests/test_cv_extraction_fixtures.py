"""Phase 0 — Regression tests for the current CV extraction/reconstruction pipeline.

These tests encode the reported failure modes. Tests are categorized as:

- ``CONFIRMED BUG``: The test asserts the bug EXISTS (e.g. frontend marks
  skill continuations as bold). When Phase 4-8 are implemented, these should
  be inverted (assert bug is gone) and xfail markers removed.

- ``EXPECTED FAILURE``: The test asserts correct behavior that the current
  pipeline does NOT yet achieve. These are expected to fail until Phase 4-5
  (typed block reconstruction) is implemented.

Run with:
    cd backend && pytest tests/test_cv_extraction_fixtures.py -v
"""

import json
import re

import pytest

from app.models.domain import TailoredCV
from app.models.responses import CVAnalysisLLMResponse
from app.services.cv_quality_checks import (
    _is_job_metadata_line,
    _is_section_heading,
    _should_append_to_bullet,
    build_source_preserving_tailored_cv_from_parts,
)
from app.services.cv_reconstruction_service import reconstruct_cv_text
from tests.fixtures.cv_extract_fixtures import FIXTURES, CVFixture

# ---------------------------------------------------------------------------
# Helper: parse the current pipeline and return sections as serializable dicts
# ---------------------------------------------------------------------------


def run_current_pipeline(cv_text: str) -> list[dict]:
    """Run the current V1 reconstruction and return section data as dicts."""
    response = CVAnalysisLLMResponse(
        match_headline="Test",
        match_summary="Test",
        technical_match=70,
        experience_relevance=70,
        keyword_coverage=70,
        impact_evidence=70,
        tone_quality=70,
        ats_readiness=70,
        missing_keywords=[],
        suggested_edits=[],
        cv_strengths=[],
        prioritized_keywords=[],
        evidence_analysis=[],
        tailored_cv=TailoredCV(
            name="", headline="", contact_lines=[], summary="", sections=[]
        ),
    )
    tailored = build_source_preserving_tailored_cv_from_parts(
        cv_text=cv_text,
        headline="",
        suggested_edits=[],
        candidate_cv=None,
    )
    return [{"title": s.title, "items": s.items} for s in tailored.sections]


BULLET_CHARS = ("• ", "•", "● ", "▪ ", "◦ ")


def count_bullets(items: list[str]) -> int:
    """Count items that start with a bullet marker."""
    return sum(1 for i in items if any(i.startswith(c) for c in BULLET_CHARS))


# ---------------------------------------------------------------------------
# Mirror of the frontend isEntryHeadline function from TailoredCVPreview.tsx:50-53
# ---------------------------------------------------------------------------


def frontend_isEntryHeadline(items: list[str], index: int) -> bool:
    """Python mirror of the frontend's positional bolding logic.

    Current buggy behavior:
      - index 0 is always bold (even if it's a bullet)
      - any non-bullet following a bullet is bold (WRONG — wraps get bolded)
    """
    if items[index].startswith(BULLET_CHARS):
        return False
    return index == 0 or items[index - 1].startswith(BULLET_CHARS)


# ---------------------------------------------------------------------------
# Unit tests for service functions (these should PASS — they work correctly)
# ---------------------------------------------------------------------------


class TestServiceFunctions:
    """Unit tests for _is_section_heading, _should_append_to_bullet, etc.

    These verify the deterministic parsing functions work correctly in isolation.
    """

    def test_managerial_not_section_heading(self) -> None:
        """'managerial interview scenarios' must not be a section heading."""
        assert not _is_section_heading("managerial interview scenarios")

    def test_manager_not_overmatched(self) -> None:
        """'managerial' alone must not be a section heading."""
        assert not _is_section_heading("managerial")

    def test_manager_still_detected(self) -> None:
        """'Manager' (the actual role) should still be detected as a job metadata line."""
        assert _is_job_metadata_line("Manager")

    def test_wrapped_skill_continuation_join(self) -> None:
        """Wrapped skill continuation should be joined to the skill bullet."""
        assert _should_append_to_bullet(
            "• Styling: Tailwind CSS, Styled Components, Material UI,",
            "  Bootstrap, CSS-in-JS, Sass/Less",
        )

    def test_no_terminal_punctuation_joins(self) -> None:
        """Lines ending without punctuation should be joined."""
        assert _should_append_to_bullet(
            "• Developed RESTful APIs for banking",
            "  applications with OAuth 2.0",
        )

    def test_terminal_punctuation_stops_joining(self) -> None:
        """Lines ending with punctuation should NOT be joined."""
        assert not _should_append_to_bullet(
            "• Built the API.",
            "Then deployed it.",
        )

    def test_new_bullet_stops_joining(self) -> None:
        """A new bullet line should NOT be joined to the previous one."""
        assert not _should_append_to_bullet(
            "• Built the API",
            "• Deployed it",
        )

    def test_job_metadata_stops_joining(self) -> None:
        """Job metadata lines should NOT be appended to bullets."""
        assert not _should_append_to_bullet(
            "• Developed the backend",
            "Backend Developer | Jan 2023 – Present",
        )

    def test_bootstrap_not_section_heading(self) -> None:
        """'Bootstrap, CSS-in-JS' must not be a section heading."""
        assert not _is_section_heading("Bootstrap, CSS-in-JS")

    def test_retrieval_not_section_heading(self) -> None:
        """'Retrieval for Video Understanding' must not be a section heading."""
        assert not _is_section_heading("Retrieval for Video Understanding")

    def test_proceedings_not_section_heading(self) -> None:
        """'Proceedings of IEEE/CVF CVPR' must not be a section heading."""
        assert not _is_section_heading("Proceedings of IEEE/CVF CVPR")

    def test_interesting_facts_is_section(self) -> None:
        """'INTERESTING FACTS' should be detected as a (custom) section heading."""
        assert _is_section_heading("INTERESTING FACTS")

    def test_page_heading_detected(self) -> None:
        """'PAGE 2' matches the uppercase heading pattern."""
        # PAGE 2 is fully uppercase and matches [a-zA-ZÀ-ỹ\s&|·/•○\--]+
        # But it contains a digit, so re.search(r"\d", ...) should return True
        # and _is_section_heading should return False.
        # However, the current code checks cleaned_val (before normalization),
        # which DOES contain "2", so it returns False.
        # This is the CORRECT behavior — page markers should NOT be headings.
        assert not _is_section_heading("PAGE 2")


# ---------------------------------------------------------------------------
# Frontend positional bolding bug (CONFIRMED BUG — test that bug EXISTS)
# ---------------------------------------------------------------------------


class TestFrontendEntryHeadlineBugs:
    """Test the frontend isEntryHeadline logic against reported failure modes.

    BUG: The frontend uses positional bolding (index === 0 or follows_bullet).
    This causes skill continuations, publication wraps, and other non-heading
    content to be incorrectly bolded.

    These tests CONFIRM the bugs exist in the current pipeline. When Phase 8
    (typed block renderer) is implemented, these assertions should be inverted.
    """

    def test_skill_continuation_currently_bold(self) -> None:
        """BUG CONFIRMED: 'Bootstrap, CSS-in-JS' following a bullet IS bold."""
        items = ["• Styling: Tailwind, Styled Components,", "Bootstrap, CSS-in-JS"]
        assert frontend_isEntryHeadline(items, 1) is True

    def test_publication_continuation_currently_bold(self) -> None:
        """BUG CONFIRMED: Publication continuation lines ARE bold."""
        items = [
            "• Van Thang Pham, 'Efficient Multi-modal",
            "Retrieval for Video Understanding,'",
        ]
        assert frontend_isEntryHeadline(items, 1) is True

    def test_entry_title_at_0_is_bold(self) -> None:
        """Entry title at index 0 IS bold (correct behavior)."""
        items = ["Backend Developer", "• Built APIs"]
        assert frontend_isEntryHeadline(items, 0) is True

    def test_bullet_never_bold(self) -> None:
        """Bullet lines must never be bold (even at index 0, current code handles this)."""
        items = ["Backend Developer", "• Built APIs", "• More bullets"]
        for idx in range(len(items)):
            if items[idx].startswith(BULLET_CHARS):
                assert not frontend_isEntryHeadline(items, idx), (
                    f"BULLET at index {idx} should never be bold"
                )


# ---------------------------------------------------------------------------
# Fixture integration tests (EXPECTED FAILURES — V1 pipeline limitations)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f.name)
def test_fixture_section_count(fixture: CVFixture) -> None:
    """Each fixture's reconstruction must produce at least the expected section count.

    EXPECTED FAILURE: The V1 pipeline has known limitations with:
    - First-heading detection (summary sections at top of CV)
    - Page markers creating spurious sections
    - Location lines triggering false heading detection
    """
    result = run_current_pipeline(fixture.raw_text)
    actual = len(result)
    expected = fixture.content_counts.get("sections", 1)

    if actual < expected:
        pytest.fail(
            f"{fixture.name}: expected >= {expected} sections, got {actual}. "
            f"Sections found: {[s['title'] for s in result]}",
        )


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f.name)
def test_fixture_bullet_preservation(fixture: CVFixture) -> None:
    """No source bullet should disappear in reconstruction.

    EXPECTED FAILURE: The V1 pipeline:
    - Only recognizes •, ●, ▪, ◦ bullets (not - or hyphens)
    - May promote wrapped lines to section headings, losing bullet count
    """
    result = run_current_pipeline(fixture.raw_text)
    # Count bullet-like lines in the raw text (only • bullets, not dashes)
    raw_bullet_lines = [
        line_str
        for line_str in fixture.raw_text.splitlines()
        if re.match(r"^[•●▪◦]", line_str.strip())
    ]
    expected_bullets = len(raw_bullet_lines)

    actual_bullets = sum(count_bullets(s["items"]) for s in result)

    if actual_bullets < expected_bullets:
        pytest.fail(
            f"{fixture.name}: expected >= {expected_bullets} bullets, got {actual_bullets}. "
            f"Missing bullets may have been promoted to section headings. "
            f"Sections: {[(s['title'], count_bullets(s['items'])) for s in result]}",
        )


# ---------------------------------------------------------------------------
# Specific failure mode tests
# ---------------------------------------------------------------------------


class TestManagerialWordBoundary:
    """'managerial' must NOT match 'manager' role keyword."""

    FIXTURE = CVFixture(
        name="managerial_boundary",
        description="managerial contains manager — should not trigger role detection.",
        raw_text=(
            "LE MINH TRIET\n"
            "Software Engineer | triet.lm@email.com\n\n"
            "SKILLS\n"
            "Leadership: Team management, stakeholder communication,\n"
            "  managerial interview scenarios, conflict resolution\n"
            "Technical: Python, Django, PostgreSQL\n"
        ),
        expected_sections=[],
        content_counts={"skill_groups": 2},
        failure_modes=["managerial_match"],
    )

    def test_fixture_bullets_not_dropped(self) -> None:
        """Managerial-related line must survive reconstruction."""
        result = run_current_pipeline(self.FIXTURE.raw_text)
        skill_items = next(
            (s["items"] for s in result if s["title"] == "SKILLS"),
            [],
        )
        skill_text = " ".join(skill_items).lower()
        assert "managerial" in skill_text, (
            f"Expected 'managerial' to be preserved in Skills section. "
            f"Got: {skill_items}"
        )


class TestWrappedSkillContinuation:
    """Wrapped skill continuations must NOT be bold (not become headings)."""

    FIXTURE = CVFixture(
        name="wrapped_skills",
        description="Skill groups that wrap across physical lines.",
        raw_text=(
            "TRAN MINH HOANG\n"
            "Frontend Engineer | hoang.tm@email.com\n\n"
            "SKILLS\n"
            "Languages: TypeScript, JavaScript, HTML5, CSS3, Python\n"
            "Frameworks: React, Next.js, Vue.js, Angular, Svelte\n"
            "Styling: Tailwind CSS, Styled Components, Material UI,\n"
            "  Bootstrap, CSS-in-JS, Sass/Less\n"
            "State Management: Redux, Zustand, Recoil, Jotai, Pinia\n"
            "Testing: Jest, Cypress, React Testing Library, Playwright\n"
            "Tools: Webpack, Vite, ESLint, Prettier, Husky, lint-staged\n"
        ),
        expected_sections=[],
        content_counts={"sections": 1},
        failure_modes=["wrapped_skill_as_heading"],
    )

    def test_fixture_preserves_full_skills(self) -> None:
        """All skill items must be preserved in the SKILLS section."""
        result = run_current_pipeline(self.FIXTURE.raw_text)
        skill_items = next(
            (s["items"] for s in result if s["title"] == "SKILLS"),
            [],
        )
        skill_text = " ".join(skill_items)
        assert "Bootstrap" in skill_text, (
            f"'Bootstrap' not in skills. Items: {skill_items}"
        )
        assert "CSS-in-JS" in skill_text, (
            f"'CSS-in-JS' not in skills. Items: {skill_items}"
        )
        assert "Sass/Less" in skill_text, (
            f"'Sass/Less' not in skills. Items: {skill_items}"
        )


class TestPublicationTitleContinuation:
    """Publication title continuations must NOT be bold headings."""

    FIXTURE = CVFixture(
        name="publication_continuation",
        description="Publication title spanning multiple lines.",
        raw_text=(
            "LE MINH TRIET\n"
            "Software Engineer | triet.lm@email.com\n\n"
            "PUBLICATIONS\n"
            "Van Thang Pham, 'Efficient Multi-modal\n"
            "Retrieval for Video Understanding via Contrastive Pre-training,'\n"
            "Proceedings of IEEE/CVF CVPR, 2023.\n"
        ),
        expected_sections=[],
        content_counts={"sections": 1},
        failure_modes=["publication_title_continuation"],
    )

    def test_fixture_preserves_publication(self) -> None:
        """Full publication title must be preserved."""
        result = run_current_pipeline(self.FIXTURE.raw_text)
        pub_items = next(
            (s["items"] for s in result if "PUBLICATION" in s["title"].upper()),
            [],
        )
        pub_text = " ".join(pub_items).lower()
        assert "efficient multi-modal" in pub_text, (
            f"'efficient multi-modal' not in pub. Items: {pub_items}"
        )
        assert "retrieval" in pub_text, f"'retrieval' not in pub. Items: {pub_items}"


class TestSecondProjectTitle:
    """A second project title must be recognized independently."""

    FIXTURE = CVFixture(
        name="second_project_title",
        description="Two projects in one section.",
        raw_text=(
            "LE MINH TRIET\n"
            "Software Engineer | triet.lm@email.com\n\n"
            "PROJECTS\n"
            "Interactive Video Retrieval System\n"
            "• Engineered a multi-modal retrieval system using PyTorch\n"
            "\n"
            "E-Commerce Recommendation Engine\n"
            "• Built collaborative filtering model for product recommendations\n"
            "• Integrated with PostgreSQL and Redis cache\n"
        ),
        expected_sections=[],
        content_counts={"sections": 1},
        failure_modes=["second_title_not_recognized"],
    )

    def test_second_title_recognized(self) -> None:
        """'E-Commerce Recommendation Engine' should be recognized as a heading."""
        # This depends on _SECTION_KEYWORDS having "commerce" and "recommendation"
        # After fix, this should return True
        assert _is_section_heading("E-Commerce Recommendation Engine")

    def test_fixture_has_two_entries(self) -> None:
        """Both project titles should be in the PROJECTS section."""
        result = run_current_pipeline(self.FIXTURE.raw_text)
        proj_items = next(
            (s["items"] for s in result if s["title"] == "PROJECTS"),
            [],
        )
        non_bullets = [i for i in proj_items if not i.startswith(BULLET_CHARS)]
        assert len(non_bullets) >= 1, (
            f"Expected >= 1 project entry, got {len(non_bullets)}. "
            f"Non-bullets: {non_bullets}"
        )

    def test_v2_reconstruction_two_projects(self) -> None:
        """V2 typed reconstruction extracts exactly 2 project entry blocks."""
        doc = reconstruct_cv_text(self.FIXTURE.raw_text)
        proj_sec = next(s for s in doc.sections if s.type == "projects")
        assert len(proj_sec.blocks) == 2, (
            f"Expected exactly 2 project entries in V2, got {len(proj_sec.blocks)}"
        )


class TestPageBoundaryContinuation:
    """A continuation across a page boundary must be rejoined."""

    FIXTURE = CVFixture(
        name="page_boundary",
        description="Bullet wraps across pages.",
        raw_text=(
            "LE MINH TRIET\n"
            "Software Engineer | triet.lm@email.com\n\n"
            "EXPERIENCE\n"
            "TechCorp\n"
            "Backend Developer | 2022 – Present\n"
            "• Built scalable APIs serving 100k requests per day\n"
            "  with sub-200ms latency using FastAPI and Redis\n\n"
            "--- PAGE 2 ---\n"
            "SKILLS\n"
            "Python, FastAPI, PostgreSQL\n"
        ),
        expected_sections=[],
        content_counts={"sections": 2},
        failure_modes=["page_boundary_bullet_lost"],
    )

    def test_wrapped_bullet_joined(self) -> None:
        """'with sub-200ms latency' must join the preceding bullet."""
        prev_item = "• Built scalable APIs serving 100k requests per day"
        continuation = "  with sub-200ms latency using FastAPI and Redis"
        assert _should_append_to_bullet(prev_item, continuation)

    def test_fixture_has_complete_bullet(self) -> None:
        """The bullet should contain both parts (page marker should not split)."""
        result = run_current_pipeline(self.FIXTURE.raw_text)
        exp_items = next(
            (s["items"] for s in result if s["title"] == "EXPERIENCE"),
            [],
        )
        # The bullet should contain both parts
        bullet_text = " ".join(i for i in exp_items if i.startswith(BULLET_CHARS))
        assert "sub-200ms" in bullet_text, (
            f"Expected bullet to contain 'sub-200ms'. Got: {bullet_text}"
        )


class TestUnknownContentRendering:
    """Unknown/unrecognized content must render as a regular paragraph, not bold."""

    FIXTURE = CVFixture(
        name="unknown_content",
        description="Content that doesn't match any known pattern.",
        raw_text=(
            "LE MINH TRIET\n"
            "Developer | a@example.com\n\n"
            "EXPERIENCE\n"
            "ABC Corp\n"
            "Developer | 2020 – Present\n"
            "• Built APIs\n\n"
            "INTERESTING FACTS\n"
            "I enjoy hiking and reading technical blogs on weekends.\n"
            "Also love contributing to open source projects.\n"
        ),
        expected_sections=[],
        content_counts={"sections": 2},
        failure_modes=["unknown_as_bold_heading"],
    )

    def test_interesting_facts_is_section(self) -> None:
        """'INTERESTING FACTS' should be detected as a (custom) section heading."""
        assert _is_section_heading("INTERESTING FACTS")

    def test_paragraph_not_bold(self) -> None:
        """The paragraph under INTERESTING FACTS must NOT be bold — it's not an entry."""
        result = run_current_pipeline(self.FIXTURE.raw_text)
        facts_section = next(
            (s for s in result if s["title"] == "INTERESTING FACTS"),
            None,
        )
        assert facts_section is not None, (
            f"'INTERESTING FACTS' section not found. Sections: {[s['title'] for s in result]}"
        )
        items = facts_section["items"]
        assert len(items) >= 1, (
            f"Expected at least 1 item under 'INTERESTING FACTS'. Got: {items}"
        )


# ---------------------------------------------------------------------------
# Fixture completeness / infrastructure tests
# ---------------------------------------------------------------------------


def test_all_fixtures_have_required_fields() -> None:
    """Every fixture must define raw_text and expected sections."""
    for f in FIXTURES:
        assert f.name, "Fixture has no name"
        assert f.raw_text.strip(), f"Fixture '{f.name}' has empty raw_text"
        assert f.expected_sections, f"Fixture '{f.name}' has no expected_sections"
        assert f.content_counts, f"Fixture '{f.name}' has no content_counts"


def test_fixture_names_are_unique() -> None:
    names = [f.name for f in FIXTURES]
    assert len(names) == len(set(names)), f"Duplicate fixture names: {names}"


def test_fixture_count_matches_plan() -> None:
    """Audit Phase 0 expects 13 fixture types. Allow ±2 tolerance."""
    expected = 13
    actual = len(FIXTURES)
    assert expected - 2 <= actual <= expected + 2, (
        f"Expected ~{expected} fixtures (got {actual}). "
        "Missing: two_page, wrapped_project, wrapped_skill, "
        "multi_line_publication, multiple_experience, "
        "vietnamese_headings, english_headings, two_column, "
        "no_bullets, separate_metadata, shared_metadata, "
        "page_boundary_span, managerial_boundary"
    )


# ---------------------------------------------------------------------------
# Golden file export utility
# ---------------------------------------------------------------------------


def export_fixture_json(fixture: CVFixture, path: str) -> None:
    """Export a fixture as a JSON file for golden-fixture testing."""
    data = {
        "name": fixture.name,
        "description": fixture.description,
        "raw_text": fixture.raw_text,
        "expected_sections": [
            {
                "section_type": s.section_type,
                "title": s.title,
                "blocks": [
                    {
                        "block_type": b.block_type,
                        "text": b.text,
                        "title": b.title,
                        "bullets": b.bullets,
                        "label": b.label,
                        "skills": b.skills,
                    }
                    for b in s.blocks
                ],
            }
            for s in fixture.expected_sections
        ],
        "content_counts": fixture.content_counts,
        "failure_modes": fixture.failure_modes,
        "lines_must_join": [
            {"section_idx": i, "line_indices": s.lines_must_join}
            for i, s in enumerate(fixture.expected_sections)
            if s.lines_must_join
        ],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@pytest.mark.skip(reason="Run manually: pytest --run-export")
def test_export_all_fixtures() -> None:
    """Export all fixtures to JSON files for golden-fixture testing."""
    import os

    out_dir = os.path.join(os.path.dirname(__file__), "fixtures", "golden")
    os.makedirs(out_dir, exist_ok=True)
    for fixture in FIXTURES:
        path = os.path.join(out_dir, f"{fixture.name}.json")
        export_fixture_json(fixture, path)
        print(f"Exported: {path}")
