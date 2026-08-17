"""Phase 5 — Block reconstruction tests.

Tests each section-specific parser in ``block_reconstruction`` against
the Phase 0 fixture corpus, plus additional targeted edge-case tests.

Run from ``backend/``:
    ./venv/bin/python -m pytest tests/test_block_reconstruction.py -q
"""

import pytest

from app.models.cv_document_v2 import (
    CVEducationBlock,
    CVEntryBlock,
    CVPublicationBlock,
    CVSkillGroupBlock,
    CVUnknownBlock,
)
from app.services.block_reconstruction import (
    _is_bullet,
    _is_date_line,
    _looks_like_entry_headline,
    _parse_award,
    _parse_certification,
    _parse_language,
    _reconstruct_education,
    _reconstruct_experience,
    _reconstruct_projects,
    _reconstruct_publications,
    _reconstruct_simple_section,
    _reconstruct_skills,
    _reconstruct_unknown_section,
    _split_authors_from_citation,
    _split_venue_from_citation,
    _strip_bullet,
    reconstruct_blocks,
)
from app.services.layout_extraction import ExtractedLine

# ---------------------------------------------------------------------------
# Helpers to create ExtractedLine lists from raw text
# ---------------------------------------------------------------------------


def _lines(text: str, **overrides) -> list[ExtractedLine]:
    """Split ``text`` on newlines and create ``ExtractedLine`` objects.

    All positional metadata defaults to page=0, x=72, y=700-i*15, width=300,
    height=14, font_size=11.0, font_weight=400 unless overridden.
    """
    raw_lines = text.split("\n")
    result = []
    for i, raw in enumerate(raw_lines):
        kw = dict(
            page=0,
            x=72,
            y=700 - i * 15,
            width=300,
            height=14,
            font_size=11.0,
            font_weight=400,
        )
        kw.update(overrides)
        result.append(ExtractedLine(text=raw, **kw))
    return result


def _bullet_lines(texts: list[str], **overrides) -> list[ExtractedLine]:
    """Create bullet lines."""
    lines = _lines("\n".join(texts), **overrides)
    for line in lines:
        if not line.text.startswith(("•",)):
            line.text = "• " + line.text
            line.normalized_text = line.text
            line.bullet_marker = "•"
    return lines


# ===========================================================================
# Experience parser tests
# ===========================================================================


class TestExperienceParser:
    """Step 5.1: Experience parser."""

    def test_single_entry_with_bullets(self):
        """One experience entry with title, org, date and bullets."""
        lines = _lines(
            "Backend Developer\n"
            "TechCorp\n"
            "Jan 2023 – Present\n"
            "• Built RESTful APIs\n"
            "• Optimized queries",
        )
        blocks = _reconstruct_experience(lines)
        assert len(blocks) == 1
        entry: CVEntryBlock = blocks[0]
        assert entry.type == "entry"
        assert entry.title == "Backend Developer"
        assert entry.organization == "TechCorp"
        assert entry.date == "Jan 2023 – Present"
        assert len(entry.bullets) == 2
        assert "Built RESTful APIs" in entry.bullets
        assert "Optimized queries" in entry.bullets

    def test_multiple_entries_same_company(self):
        """Multiple roles at one employer — each becomes a separate entry."""
        lines = _lines(
            "VNG Corporation\n"
            "Senior Software Engineer | Mar 2024 – Present\n"
            "• Lead a team of 5 engineers\n\n"
            "Software Engineer | Jan 2022 – Feb 2024\n"
            "• Built push notification service\n\n"
            "Intern Software Engineer | Jun 2021 – Dec 2021\n"
            "• Developed internal dashboard",
        )
        blocks = _reconstruct_experience(lines)
        assert len(blocks) == 3
        assert blocks[0].title == "Senior Software Engineer"
        assert blocks[0].organization == "VNG Corporation"
        assert blocks[1].title == "Software Engineer"
        assert blocks[1].organization == "VNG Corporation"
        assert blocks[2].title == "Intern Software Engineer"
        assert blocks[2].organization == "VNG Corporation"

    def test_shared_metadata_line(self):
        """Role at Company | Location | Date on one line."""
        lines = _lines(
            "Software Engineer at Viettel Digital | Hanoi | 2020-2024\n"
            "- Developed microservices\n"
            "- Built React frontend",
        )
        blocks = _reconstruct_experience(lines)
        assert len(blocks) == 1
        entry: CVEntryBlock = blocks[0]
        assert entry.title == "Software Engineer"
        assert entry.organization == "Viettel Digital"
        assert entry.location == "Hanoi"
        assert entry.date == "2020-2024"
        assert len(entry.bullets) == 2

    def test_wrapped_bullet_continuation(self):
        """Bullet continuation on next line (lowercase start) is joined."""
        lines = _lines(
            "Customer Churn Prediction System\n"
            "• Developed an ML pipeline using Scikit-learn and XGBoost\n"
            "  that reduced customer churn by 23%",
        )
        blocks = _reconstruct_experience(lines)
        assert len(blocks) == 1
        assert len(blocks[0].bullets) == 1
        assert "that reduced customer churn by 23%" in blocks[0].bullets[0]

    def test_no_bullet_lines(self):
        """Dash-prefixed bullets are recognized."""
        lines = _lines(
            "DevOps Engineer\n- Designed CI/CD pipelines\n- Reduced deployment time",
        )
        blocks = _reconstruct_experience(lines)
        assert len(blocks) == 1
        entry: CVEntryBlock = blocks[0]
        assert entry.title == "DevOps Engineer"
        assert len(entry.bullets) == 2
        assert "Designed CI/CD pipelines" in entry.bullets

    def test_entry_boundary_uses_combined_signals(self):
        """Date+title patterns separate entries, not 'line after bullet'."""
        lines = _lines(
            "Backend Developer\nJan 2023 – Present\n• Built APIs",
        )
        blocks = _reconstruct_experience(lines)
        assert len(blocks) == 1
        assert blocks[0].date == "Jan 2023 – Present"

    def test_multiple_positions_same_org(self):
        """Three roles at VNG — each is a separate entry."""
        lines = _lines(
            "Senior Software Engineer | Mar 2024 – Present\n"
            "• Lead team\n\n"
            "Software Engineer | Jan 2022 – Feb 2024\n"
            "• Built service\n\n"
            "Intern | Jun 2021 – Dec 2021\n"
            "• Developed dashboard",
        )
        blocks = _reconstruct_experience(lines)
        assert len(blocks) == 3
        assert blocks[0].title == "Senior Software Engineer"
        assert blocks[1].title == "Software Engineer"
        assert blocks[2].title == "Intern"

    def test_consecutive_entries_without_blank_lines(self):
        """A new role must not be swallowed by the preceding bullet."""
        lines = _lines(
            "VNG Corporation\n"
            "Senior Software Engineer | Mar 2024 – Present\n"
            "• Led the platform team.\n"
            "Software Engineer | Jan 2022 – Feb 2024\n"
            "• Built the notification service.",
        )
        blocks = _reconstruct_experience(lines)
        assert [block.title for block in blocks] == [
            "Senior Software Engineer",
            "Software Engineer",
        ]
        assert all(block.organization == "VNG Corporation" for block in blocks)

    def test_pipe_metadata_preserves_location_and_date(self):
        lines = _lines(
            "Backend Engineer | TechCorp | Hanoi, Vietnam | Jan 2022 – Present\n"
            "• Built APIs.",
        )
        entry = _reconstruct_experience(lines)[0]
        assert entry.organization == "TechCorp"
        assert entry.location == "Hanoi, Vietnam"
        assert entry.date == "Jan 2022 – Present"

    def test_org_first_separate_role_location_and_blank_before_bullets(self):
        lines = _lines(
            "TechCorp\n"
            "Backend Developer\n"
            "Hanoi, Vietnam\n"
            "Jan 2023 – Present\n\n"
            "• Built APIs.",
        )
        entry = _reconstruct_experience(lines)[0]
        assert entry.organization == "TechCorp"
        assert entry.title == "Backend Developer"
        assert entry.location == "Hanoi, Vietnam"
        assert entry.date == "Jan 2023 – Present"
        assert entry.bullets == ["Built APIs."]

    @pytest.mark.parametrize(
        "metadata",
        [
            "Backend Engineer | TechCorp | Hanoi | 2023",
            "Backend Engineer at TechCorp | Hanoi | 2023",
        ],
    )
    def test_shared_metadata_keeps_bullets_after_layout_blank(self, metadata):
        entry = _reconstruct_experience(
            _lines(
                f"{metadata}\n\n• Built APIs.",
            )
        )[0]
        assert entry.bullets == ["Built APIs."]


# ===========================================================================
# Projects parser tests
# ===========================================================================


class TestProjectsParser:
    """Step 5.2: Projects parser."""

    def test_single_project_with_bullets(self):
        """One project entry with title and bullets."""
        lines = _lines(
            "E-Commerce Platform\n• Built shopping cart\n• Deployed on AWS",
        )
        blocks = _reconstruct_projects(lines)
        assert len(blocks) == 1
        entry: CVEntryBlock = blocks[0]
        assert entry.type == "entry"
        assert entry.title == "E-Commerce Platform"
        assert len(entry.bullets) == 2

    def test_wrapped_project_bullet(self):
        """Wrapped bullet continuation is joined, not treated as heading."""
        lines = _lines(
            "Interactive Video Retrieval System\n"
            "• Built a multi-modal retrieval system using\n"
            "  Transformers and GNN",
        )
        blocks = _reconstruct_projects(lines)
        assert len(blocks) == 1
        assert len(blocks[0].bullets) == 1
        assert "Transformers and GNN" in blocks[0].bullets[0]

    def test_two_projects_independent(self):
        """Second project title recognized independently."""
        lines = _lines(
            "Project Alpha\n"
            "• First project bullet\n\n"
            "Project Beta\n"
            "• Second project bullet",
        )
        blocks = _reconstruct_projects(lines)
        assert len(blocks) == 2
        assert blocks[0].title == "Project Alpha"
        assert blocks[1].title == "Project Beta"

    def test_project_with_tech_metadata(self):
        """Technology metadata stored as subtitle."""
        lines = _lines(
            "Data Pipeline\n"
            "Python, Spark, Airflow\n"
            "• Built pipeline\n"
            "• Processed 1M rows",
        )
        blocks = _reconstruct_projects(lines)
        assert len(blocks) == 1
        assert blocks[0].title == "Data Pipeline"
        assert (
            "Python, Spark, Airflow" in blocks[0].subtitle
            or blocks[0].subtitle == "Python, Spark, Airflow"
        )

    def test_wrapped_bullet_does_not_skip_following_bullets(self):
        lines = _lines(
            "Project Alpha\n"
            "• Built a distributed\n"
            "  processing system\n"
            "• Deployed safely.\n"
            "• Monitored uptime.",
        )
        entry = _reconstruct_projects(lines)[0]
        assert entry.bullets == [
            "Built a distributed processing system",
            "Deployed safely.",
            "Monitored uptime.",
        ]

    def test_project_context_and_date_are_preserved(self):
        lines = _lines(
            "Video Retrieval System\n"
            "Research Prototype | 2023\n"
            "PyTorch, Transformers, FAISS\n"
            "• Built retrieval pipeline.",
        )
        entry = _reconstruct_projects(lines)[0]
        assert entry.title == "Video Retrieval System"
        assert "Research Prototype" in (entry.subtitle or "")
        assert "PyTorch, Transformers, FAISS" in (entry.subtitle or "")
        assert entry.date == "2023"

    def test_projects_without_blank_lines_remain_independent(self):
        blocks = _reconstruct_projects(
            _lines(
                "Project Alpha\n• Built feature\nProject Beta\n• Shipped release",
            )
        )
        assert [block.title for block in blocks] == ["Project Alpha", "Project Beta"]

    def test_project_role_context_is_not_a_second_project(self):
        blocks = _reconstruct_projects(
            _lines(
                "Video Retrieval System\n"
                "Backend Developer\n"
                "2023\n"
                "• Built retrieval pipeline.",
            )
        )
        assert len(blocks) == 1
        assert blocks[0].title == "Video Retrieval System"
        assert blocks[0].subtitle == "Backend Developer"
        assert blocks[0].date == "2023"

    def test_project_keeps_bullets_after_layout_blank(self):
        entry = _reconstruct_projects(
            _lines(
                "Project Alpha\n2023\n\n• Built it.",
            )
        )[0]
        assert entry.bullets == ["Built it."]


# ===========================================================================
# Skills parser tests
# ===========================================================================


class TestSkillsParser:
    """Step 5.3: Skills parser."""

    def test_skill_groups_with_labels(self):
        """Label: item1, item2 → skill_group blocks."""
        lines = _lines(
            "Backend: Python, FastAPI, Django\nDatabase: PostgreSQL, Redis",
        )
        blocks = _reconstruct_skills(lines)
        assert len(blocks) == 2
        assert blocks[0].type == "skill_group"
        assert blocks[0].label == "Backend"
        assert blocks[0].skills == ["Python", "FastAPI", "Django"]
        assert blocks[1].label == "Database"
        assert blocks[1].skills == ["PostgreSQL", "Redis"]

    def test_wrapped_skill_continuation(self):
        """Wrapped skill continuation joined before splitting."""
        lines = _lines(
            "Styling: Tailwind CSS, Styled Components, Material UI,\n"
            "  Bootstrap, CSS-in-JS, Sass/Less",
        )
        blocks = _reconstruct_skills(lines)
        assert len(blocks) == 1
        sg: CVSkillGroupBlock = blocks[0]
        assert sg.label == "Styling"
        assert "Bootstrap" in sg.skills
        assert "CSS-in-JS" in sg.skills
        assert "Sass/Less" in sg.skills

    def test_no_skill_as_heading(self):
        """Skill items are never treated as entry headings."""
        lines = _lines(
            "Java, Spring Boot, Python, FastAPI, PostgreSQL, Docker",
        )
        blocks = _reconstruct_skills(lines)
        # This is a plain line (no label: format), so it becomes a paragraph
        # The "Skills" heading would be filtered out by detect_sections()
        assert len(blocks) == 1
        assert any(b.type == "skill_group" for b in blocks) or any(
            b.type == "paragraph" for b in blocks
        )

    def test_managerial_word_not_heading(self):
        """'managerial' word should not trigger heading detection."""
        lines = _lines(
            "Leadership: Team management, stakeholder communication,\n"
            "  managerial interview scenarios, conflict resolution\n"
            "Technical: Python, Django, PostgreSQL, Redis",
        )
        blocks = _reconstruct_skills(lines)
        assert len(blocks) == 2
        assert blocks[0].label == "Leadership"
        assert "managerial interview scenarios" in blocks[0].skills
        assert blocks[1].label == "Technical"

    def test_wrapped_skill_not_bold(self):
        """Wrapped skill continuation must NOT become a bold heading."""
        lines = _lines(
            "AI/ML: PyTorch, Hugging Face Transformers, GNN",
        )
        blocks = _reconstruct_skills(lines)
        assert len(blocks) == 1
        sg: CVSkillGroupBlock = blocks[0]
        assert sg.type == "skill_group"
        assert "Hugging Face Transformers" in sg.skills
        assert "GNN" in sg.skills

    def test_complex_skill_names(self):
        """Skills with mixed case, numbers, symbols."""
        lines = _lines(
            "Tools: C++, Node.js, SQL, React 18, GraphQL",
        )
        blocks = _reconstruct_skills(lines)
        assert len(blocks) == 1
        sg: CVSkillGroupBlock = blocks[0]
        assert "C++" in sg.skills
        assert "Node.js" in sg.skills
        assert "SQL" in sg.skills
        assert "React 18" in sg.skills

    def test_indented_skill_continuation_without_trailing_comma(self):
        blocks = _reconstruct_skills(
            _lines(
                "AI/ML Research: PyTorch, Transformers\n  GNN",
            )
        )
        assert len(blocks) == 1
        assert blocks[0].skills == ["PyTorch", "Transformers GNN"]

    def test_mixed_delimiter_skill_line_falls_back_without_data_loss(self):
        source = "Backend: Python, FastAPI; Django"
        blocks = _reconstruct_skills(_lines(source))
        assert len(blocks) == 1
        assert blocks[0].type == "paragraph"
        assert blocks[0].text == source


# ===========================================================================
# Publications parser tests
# ===========================================================================


class TestPublicationsParser:
    """Step 5.4: Publications parser."""

    def test_single_citation(self):
        """Single publication citation parsed correctly."""
        lines = _lines(
            "Van Thang Pham, Nguyen Van Duy, 'Efficient Multi-modal Retrieval for Video Understanding via Contrastive Pre-training,' IEEE ICIP 2022.",
        )
        blocks = _reconstruct_publications(lines)
        assert len(blocks) == 1
        pub: CVPublicationBlock = blocks[0]
        assert pub.type == "publication"
        assert pub.authors == "Van Thang Pham, Nguyen Van Duy"
        assert pub.date == "2022"

    def test_multi_line_citation_joined(self):
        """Multi-line citation is joined into one block."""
        lines = _lines(
            "Van Thang Pham, Nguyen Van Duy, 'Efficient Multi-modal\n"
            "Retrieval for Video Understanding via Contrastive Pre-training,'\n"
            "Proceedings of the IEEE/CVF Conference on Computer Vision\n"
            "and Pattern Recognition (CVPR), 2023.",
        )
        blocks = _reconstruct_publications(lines)
        assert len(blocks) == 1
        pub: CVPublicationBlock = blocks[0]
        assert pub.type == "publication"
        # Title should be joined
        assert "Multi-modal" in pub.title
        assert "Pre-training" in pub.title
        # Authors should be extracted
        assert "Van Thang Pham" in (pub.authors or "")

    def test_citation_not_broken_into_bold(self):
        """Publication continuation lines must NOT become bold headings."""
        lines = _lines(
            "Le Thi Mai, Van Thang Pham, 'Self-Supervised Representation\n"
            "Learning for Industrial Anomaly Detection,' Journal of Machine\n"
            "Learning Research, vol. 24, no. 12, pp. 1-35, 2023.",
        )
        blocks = _reconstruct_publications(lines)
        assert len(blocks) == 1
        pub: CVPublicationBlock = blocks[0]
        assert pub.type == "publication"
        assert "Self-Supervised Representation" in pub.title

    def test_under_review_status(self):
        """'Under Review' is captured as status."""
        lines = _lines(
            "Tran Minh Hoang, 'Adaptive Attention Mechanisms for Real-Time\n"
            "Object Detection,' ACM MM, 2024. — Under Review",
        )
        blocks = _reconstruct_publications(lines)
        assert len(blocks) == 1
        pub: CVPublicationBlock = blocks[0]
        assert pub.status == "Under Review"

    def test_multiple_publications(self):
        """Multiple publications each become a separate block."""
        lines = _lines(
            "Author A, 'Title A,' Venue A, 2022.\n\n"
            "Author B, 'Title B,' Venue B, 2023.",
        )
        blocks = _reconstruct_publications(lines)
        assert len(blocks) == 2
        assert blocks[0].type == "publication"
        assert blocks[1].type == "publication"

    def test_adjacent_publications_without_blank_line(self):
        lines = _lines(
            "A. Author, 'First Paper,' IEEE, 2022.\n"
            "B. Author, 'Second Paper,' ACM, 2023.",
        )
        blocks = _reconstruct_publications(lines)
        assert len(blocks) == 2
        assert blocks[0].title == "First Paper,"
        assert blocks[1].title == "Second Paper,"

    def test_title_case_venue_continues_incomplete_citation(self):
        blocks = _reconstruct_publications(
            _lines(
                "A. Author, 'Paper,'\nIEEE Transactions\n2024.",
            )
        )
        assert len(blocks) == 1
        publication = blocks[0]
        assert "IEEE Transactions" in (publication.venue or "")
        assert publication.date == "2024"


# ===========================================================================
# Education parser tests
# ===========================================================================


class TestEducationParser:
    """Step 5.5: Education parser."""

    def test_single_education_record(self):
        """Institution, degree, date parsed correctly."""
        lines = _lines(
            "Kỹ sư Công nghệ Thông tin\nĐại học Bách Khoa TP.HCM\n2017 – 2021",
        )
        blocks = _reconstruct_education(lines)
        assert len(blocks) == 1
        edu: CVEducationBlock = blocks[0]
        assert edu.degree == "Kỹ sư Công nghệ Thông tin"
        assert edu.institution == "Đại học Bách Khoa TP.HCM"
        assert edu.date == "2017 – 2021"

    def test_education_with_gpa(self):
        """GPA captured as detail."""
        lines = _lines(
            "Master of Science in Data Science\n"
            "FPT University | 2019 – 2021 | GPA: 3.7/4.0",
        )
        blocks = _reconstruct_education(lines)
        assert len(blocks) == 1
        edu: CVEducationBlock = blocks[0]
        assert edu.degree == "Master of Science"
        assert edu.field == "Data Science"
        assert edu.institution == "FPT University"
        assert edu.date == "2019 – 2021"
        assert any("GPA" in d for d in edu.details)

    def test_multiple_education_records(self):
        """Multiple education records parsed independently."""
        lines = _lines(
            "Master of Science in Data Science\n"
            "FPT University | 2019 – 2021\n\n"
            "Bachelor of Science in Mathematics\n"
            "HCMC University of Science | 2015 – 2019",
        )
        blocks = _reconstruct_education(lines)
        assert len(blocks) == 2
        assert blocks[0].degree == "Master of Science"
        assert blocks[0].field == "Data Science"
        assert blocks[1].degree == "Bachelor of Science"
        assert blocks[1].field == "Mathematics"

    def test_field_and_capitalized_location_are_identified(self):
        lines = _lines(
            "Bachelor of Science\n"
            "Computer Science\n"
            "FPT University\n"
            "Hanoi, Vietnam\n"
            "2019 – 2023",
        )
        edu = _reconstruct_education(lines)[0]
        assert edu.degree == "Bachelor of Science"
        assert edu.field == "Computer Science"
        assert edu.institution == "FPT University"
        assert edu.location == "Hanoi, Vietnam"
        assert edu.date == "2019 – 2023"

    def test_consecutive_education_records_without_blank_lines(self):
        blocks = _reconstruct_education(
            _lines(
                "Master of Science in Data Science\n"
                "FPT University\n"
                "2019 – 2021\n"
                "Bachelor of Science in Mathematics\n"
                "HCMC University of Science\n"
                "2015 – 2019",
            )
        )
        assert len(blocks) == 2
        assert blocks[0].institution == "FPT University"
        assert blocks[0].date == "2019 – 2021"
        assert blocks[1].institution == "HCMC University of Science"
        assert blocks[1].date == "2015 – 2019"

    def test_embedded_degree_field_is_separated(self):
        edu = _reconstruct_education(
            _lines(
                "Bachelor of Science in Computer Science\nFPT University\n2019 – 2023",
            )
        )[0]
        assert edu.degree == "Bachelor of Science"
        assert edu.field == "Computer Science"

    def test_institution_first_records_without_blank_lines(self):
        blocks = _reconstruct_education(
            _lines(
                "FPT University\n"
                "Bachelor of Science in Data Science\n"
                "2015 – 2019\n"
                "Hanoi University\n"
                "Master of Science in Computer Science\n"
                "2019 – 2021",
            )
        )
        assert len(blocks) == 2
        assert blocks[0].institution == "FPT University"
        assert blocks[0].degree == "Bachelor of Science"
        assert blocks[0].date == "2015 – 2019"
        assert blocks[1].institution == "Hanoi University"
        assert blocks[1].degree == "Master of Science"
        assert blocks[1].date == "2019 – 2021"


# ===========================================================================
# Simple-section parsers tests
# ===========================================================================


class TestSimpleSectionParsers:
    """Step 5.6: Certifications, languages, awards, activities, interests."""

    def test_certifications(self):
        """Certifications with pipe-separated metadata."""
        lines = _lines(
            "AWS Certified Solutions Architect – Associate | 2023\n"
            "Google Cloud Professional Data Engineer | 2023",
        )
        blocks = _reconstruct_simple_section(lines, "certifications")
        assert len(blocks) == 2
        assert all(b.type == "entry" for b in blocks)
        assert blocks[0].title == "AWS Certified Solutions Architect – Associate"
        assert blocks[1].title == "Google Cloud Professional Data Engineer"

    def test_two_field_certification_classifies_date(self):
        entry = _reconstruct_simple_section(
            _lines("AWS Certified Solutions Architect | 2023"),
            "certifications",
        )[0]
        assert entry.organization is None
        assert entry.date == "2023"

    def test_languages(self):
        """Languages with proficiency in parentheses."""
        lines = _lines(
            "Tiếng Việt (Bản xứ)\nTiếng Anh (IELTS 7.0 – thành thạo)",
        )
        blocks = _reconstruct_simple_section(lines, "languages")
        assert len(blocks) == 2
        assert blocks[0].title == "Tiếng Việt"
        assert blocks[0].subtitle == "Bản xứ"
        assert blocks[1].title == "Tiếng Anh"

    def test_awards(self):
        """Awards with year."""
        lines = _lines(
            "Best Paper Award (2023)\nDean's List (2021)",
        )
        blocks = _reconstruct_simple_section(lines, "awards")
        assert len(blocks) == 2
        assert blocks[0].title == "Best Paper Award"
        assert blocks[0].date == "2023"

    def test_activities_paragraph(self):
        """Activities become paragraph blocks."""
        lines = _lines(
            "Hackathon organizer\nOpen source contributor",
        )
        blocks = _reconstruct_simple_section(lines, "activities")
        assert all(b.type == "paragraph" for b in blocks)
        assert len(blocks) == 2

    def test_interests_paragraph(self):
        """Interests become paragraph blocks."""
        lines = _lines(
            "Photography\nHiking",
        )
        blocks = _reconstruct_simple_section(lines, "interests")
        assert all(b.type == "paragraph" for b in blocks)


# ===========================================================================
# Unknown section fallback
# ===========================================================================


class TestUnknownSectionFallback:
    """Step 5.7: Unknown-section fallback."""

    def test_unknown_becomes_unknown_block(self):
        """Unknown content becomes CVUnknownBlock, not bold."""
        lines = _lines("Some unclassified content here")
        blocks = _reconstruct_unknown_section(lines)
        assert len(blocks) == 1
        assert blocks[0].type == "unknown"
        assert isinstance(blocks[0], CVUnknownBlock)

    def test_preserves_content_neutrally(self):
        """Content is preserved with neutral formatting."""
        lines = _lines("Custom content that doesn't match any pattern")
        blocks = _reconstruct_unknown_section(lines)
        assert len(blocks) == 1
        assert "Custom content that doesn't match any pattern" in blocks[0].lines


# ===========================================================================
# Entry-point dispatch test
# ===========================================================================


class TestReconstructBlocksDispatch:
    """Test the ``reconstruct_blocks()`` dispatch function."""

    def test_experience_dispatch(self):
        lines = _lines("Engineer\nCompany\n2020-2022\n• Bullet")
        blocks = reconstruct_blocks("experience", lines)
        assert blocks and blocks[0].type == "entry"

    def test_projects_dispatch(self):
        lines = _lines("Project X\n• Bullet")
        blocks = reconstruct_blocks("projects", lines)
        assert blocks and blocks[0].type == "entry"

    def test_skills_dispatch(self):
        lines = _lines("Skills: Python, Java")
        blocks = reconstruct_blocks("skills", lines)
        assert blocks and blocks[0].type == "skill_group"

    def test_publications_dispatch(self):
        lines = _lines("Author, 'Title,' Venue, 2022.")
        blocks = reconstruct_blocks("publications", lines)
        assert blocks and blocks[0].type == "publication"

    def test_education_dispatch(self):
        lines = _lines("University\nDegree\n2018-2022")
        blocks = reconstruct_blocks("education", lines)
        assert blocks and blocks[0].type in ("education", "paragraph")

    def test_certifications_dispatch(self):
        lines = _lines("Certification | 2023")
        blocks = reconstruct_blocks("certifications", lines)
        assert blocks and blocks[0].type == "entry"

    def test_languages_dispatch(self):
        lines = _lines("English (Fluent)")
        blocks = reconstruct_blocks("languages", lines)
        assert blocks and blocks[0].type == "entry"

    def test_custom_dispatch(self):
        lines = _lines("Custom section content")
        blocks = reconstruct_blocks("custom", lines)
        assert blocks and blocks[0].type == "unknown"

    def test_empty_lines(self):
        """Empty lines return empty block list."""
        for section_type in (
            "experience",
            "skills",
            "projects",
            "education",
            "publications",
            "certifications",
            "languages",
            "custom",
        ):
            assert reconstruct_blocks(section_type, []) == []


# ===========================================================================
# Integration: fixture-based tests against Phase 0 fixtures
# ===========================================================================


class TestFixtureIntegration:
    """Run Phase 5 reconstruction against the Phase 0 fixture corpus."""

    @pytest.fixture
    def two_page_cv_lines(self):
        """Two-page CV lines — manually crafted for the reconstruction step."""
        return _lines(
            "TÓM TẮT\n"
            "Kỹ sư backend với 3 năm kinh nghiệm.\n\n"
            "KINH NGHIỆM LÀM VIỆC\n"
            "TechCorp\n"
            "Backend Developer | Jan 2023 – Present\n"
            "• Built RESTful API\n"
            "• Optimized queries\n\n"
            "ABC Solution\n"
            "Junior Developer | Jun 2021 – Dec 2022\n"
            "• Developed payment\n\n"
            "DỰ ÁN\n"
            "Video Retrieval System\n"
            "• Built multi-modal retrieval using\n"
            "  Transformers and GNN\n\n"
            "KỸ NĂNG\n"
            "Backend: Python, FastAPI, Django, Node.js\n"
            "Database: PostgreSQL, Redis, MongoDB\n",
        )

    def test_experience_section(self, two_page_cv_lines):
        """Experience section: 2 entries, correct metadata."""
        # Simulate what detect_sections would pass to the experience parser
        exp_lines = _lines(
            "TechCorp\n"
            "Backend Developer | Jan 2023 – Present\n"
            "• Built RESTful API\n"
            "• Optimized queries\n\n"
            "ABC Solution\n"
            "Junior Developer | Jun 2021 – Dec 2022\n"
            "• Developed payment",
        )
        blocks = _reconstruct_experience(exp_lines)
        assert len(blocks) == 2
        assert blocks[0].title == "Backend Developer"
        assert blocks[0].organization == "TechCorp"
        assert blocks[0].date == "Jan 2023 – Present"
        assert blocks[1].title == "Junior Developer"
        assert blocks[1].organization == "ABC Solution"

    def test_projects_section_wrapped_bullet(self):
        """Wrapped project bullets are joined, not separate headings."""
        proj_lines = _lines(
            "Video Retrieval System\n"
            "• Built multi-modal retrieval using\n"
            "  Transformers and GNN",
        )
        blocks = _reconstruct_projects(proj_lines)
        assert len(blocks) == 1
        assert len(blocks[0].bullets) == 1
        assert "Transformers and GNN" in blocks[0].bullets[0]

    def test_skills_section(self):
        """Skills: 2 groups parsed correctly."""
        skill_lines = _lines(
            "Backend: Python, FastAPI, Django, Node.js\n"
            "Database: PostgreSQL, Redis, MongoDB",
        )
        blocks = _reconstruct_skills(skill_lines)
        assert len(blocks) == 2
        assert blocks[0].label == "Backend"
        assert blocks[1].label == "Database"
        assert len(blocks[0].skills) == 4
        assert len(blocks[1].skills) == 3

    def test_wrapped_skill_continuation_not_bold(self):
        """Wrapped skill continuation must NOT become a heading."""
        skill_lines = _lines(
            "Styling: Tailwind CSS, Styled Components, Material UI,\n"
            "  Bootstrap, CSS-in-JS, Sass/Less",
        )
        blocks = _reconstruct_skills(skill_lines)
        assert len(blocks) == 1
        assert blocks[0].type == "skill_group"
        assert "Bootstrap" in blocks[0].skills
        assert "CSS-in-JS" in blocks[0].skills
        assert "Sass/Less" in blocks[0].skills

    def test_publication_citation_joined(self):
        """Multi-line publication citation joined into one block."""
        pub_lines = _lines(
            "Nguyen Van Duy, Le Thi Mai, 'Multi-modal Video Retrieval using\n"
            "Graph Neural Networks and Transformers,' IEEE ICIP 2022.",
        )
        blocks = _reconstruct_publications(pub_lines)
        assert len(blocks) == 1
        pub: CVPublicationBlock = blocks[0]
        assert pub.type == "publication"
        assert "Graph Neural Networks" in pub.title


# ===========================================================================
# Unit tests for helper functions
# ===========================================================================


class TestHelperFunctions:
    """Unit tests for individual helper functions."""

    def test_is_bullet(self):
        line = ExtractedLine(text="• something", page=0, x=0, y=0, width=0, height=0)
        assert _is_bullet(line, "• something") is True
        assert _is_bullet(line, "● something") is True
        assert _is_bullet(line, "- something") is True

    def test_strip_bullet(self):
        assert _strip_bullet("• something") == "something"
        assert _strip_bullet("● something") == "something"
        assert _strip_bullet("- something") == "something"

    def test_is_date_line(self):
        assert _is_date_line("2020-2022") is True
        assert _is_date_line("Jan 2021 – Dec 2022") is True
        assert _is_date_line("2020 – Present") is True
        assert _is_date_line("Backend Developer") is False

    def test_looks_like_entry_headline_bold(self):
        line = ExtractedLine(
            text="Backend Developer",
            page=0,
            x=72,
            y=600,
            width=200,
            height=14,
            font_size=12.0,
            font_weight=700,
        )
        assert _looks_like_entry_headline(line, "Backend Developer", [], 0) is True

    def test_looks_like_entry_headline_title_case(self):
        line = ExtractedLine(
            text="Backend Developer",
            page=0,
            x=72,
            y=600,
            width=200,
            height=14,
            font_size=11.0,
            font_weight=400,
        )
        # Title-case short phrase should be a headline
        assert _looks_like_entry_headline(line, "Backend Developer", [], 0) is True

    def test_looks_like_entry_headline_date_rejected(self):
        line = ExtractedLine(
            text="2020-2022",
            page=0,
            x=72,
            y=600,
            width=200,
            height=14,
            font_size=11.0,
            font_weight=400,
        )
        assert _looks_like_entry_headline(line, "2020-2022", [], 0) is False

    def test_looks_like_entry_headline_bullet_rejected(self):
        line = ExtractedLine(
            text="• something",
            page=0,
            x=72,
            y=600,
            width=200,
            height=14,
            font_size=11.0,
            font_weight=400,
        )
        assert _is_bullet(line, "• something") is True

    def test_split_authors_basic(self):
        authors, rest = _split_authors_from_citation(
            "Van Thang Pham, Nguyen Van Duy, 'Title,' Venue, 2022.",
        )
        assert authors == "Van Thang Pham, Nguyen Van Duy"
        assert "Title" in rest

    def test_split_venue_basic(self):
        venue, date, _status = _split_venue_from_citation("IEEE ICIP 2022")
        assert venue == "IEEE ICIP"
        assert date == "2022"

    def test_split_venue_with_status(self):
        venue, date, status = _split_venue_from_citation("ACM MM, 2024. — Under Review")
        assert venue == "ACM MM"
        assert date == "2024"
        assert status == "Under Review"

    def test_parse_certification_pipe(self):
        lines = _lines("AWS Certified | Issuer | 2023")
        result, _consumed = _parse_certification(lines, 0)
        assert result is not None
        assert result.title == "AWS Certified"
        assert result.date == "2023"

    def test_parse_language_paren(self):
        lines = _lines("English (Fluent)")
        result, _consumed = _parse_language(lines, 0)
        assert result is not None
        assert result.title == "English"
        assert result.subtitle == "Fluent"

    def test_parse_award_year(self):
        lines = _lines("Best Paper (2023)")
        result, _consumed = _parse_award(lines, 0)
        assert result is not None
        assert result.title == "Best Paper"
        assert result.date == "2023"
