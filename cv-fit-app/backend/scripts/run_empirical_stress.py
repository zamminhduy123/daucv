"""Standalone Empirical Stress Harness Runner.

Runs empirical stress tests against block_reconstruction.py and section_detector.py
without relying on external subprocesses or shell permission prompts.
Outputs empirical stress findings directly to stdout / report files.
"""

import sys
import traceback
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.cv_document_v2 import (  # noqa: E402
    CVEntryBlock,
    CVSkillGroupBlock,
)
from app.services.block_reconstruction import (  # noqa: E402
    attach_reconstruction_metadata,
    reconstruct_blocks,
)
from app.services.layout_extraction import ExtractedLine  # noqa: E402
from app.services.section_detector import detect_sections  # noqa: E402
from app.services.section_vocabulary import classify_heading  # noqa: E402


def _line(
    text: str, line_id: str | None = None, page: int = 0, y: float = 700.0, **overrides
) -> ExtractedLine:
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


def run_empirical_harness():
    results = []

    def report(name, status, details=""):
        results.append((name, status, details))
        status_symbol = (
            "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "WARN")
        )
        print(f"[{status_symbol}] {name}: {details}")

    print("======================================================================")
    print("STARTING EMPIRICAL STRESS SUITE: block_reconstruction & section_detector")
    print("======================================================================\n")

    # -------------------------------------------------------------------------
    # Scenario 1: Empty text & whitespace
    # -------------------------------------------------------------------------
    try:
        b1 = reconstruct_blocks("experience", [])
        b2 = reconstruct_blocks("skills", [])
        doc1 = detect_sections([])
        if b1 == [] and b2 == [] and len(doc1.sections) == 0:
            report(
                "Scenario 1.1: Completely empty input lists",
                "PASS",
                "Returned empty output safely without exception.",
            )
        else:
            report(
                "Scenario 1.1: Completely empty input lists",
                "FAIL",
                f"Unexpected output: {b1=}, {b2=}",
            )
    except Exception as e:
        report(
            "Scenario 1.1: Completely empty input lists",
            "FAIL",
            f"Crash: {e}\n{traceback.format_exc()}",
        )

    try:
        lines_ws = [_line("   "), _line("\t\n"), _line("  ")]
        b_ws = reconstruct_blocks("experience", lines_ws)
        doc_ws = detect_sections(lines_ws)
        report(
            "Scenario 1.2: Whitespace-only lines",
            "PASS",
            f"Handled {len(lines_ws)} whitespace lines safely.",
        )
    except Exception as e:
        report("Scenario 1.2: Whitespace-only lines", "FAIL", f"Crash: {e}")

    try:
        line_none_id = _line("Software Engineer", line_id=None)
        b_none = reconstruct_blocks("experience", [line_none_id])
        if len(b_none) == 1 and len(b_none[0].source_line_ids) > 0:
            report(
                "Scenario 1.3: Line with source_line_id=None",
                "PASS",
                f"Generated on-the-fly provenance ID: {b_none[0].source_line_ids}",
            )
        else:
            report(
                "Scenario 1.3: Line with source_line_id=None",
                "WARN",
                f"Missing source line IDs: {b_none[0].source_line_ids if b_none else 'No blocks'}",
            )
    except Exception as e:
        report("Scenario 1.3: Line with source_line_id=None", "FAIL", f"Crash: {e}")

    # -------------------------------------------------------------------------
    # Scenario 2: Single characters
    # -------------------------------------------------------------------------
    chars = ["a", "1", ".", ":", "|", "•", "-", "@", "x", "Đ"]
    single_char_crashes = []
    for c in chars:
        try:
            line_c = _line(c, f"id-{ord(c)}")
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
                reconstruct_blocks(stype, [line_c])
            detect_sections([line_c])
        except Exception as e:
            single_char_crashes.append((c, str(e)))

    if not single_char_crashes:
        report(
            "Scenario 2.1: Single character inputs",
            "PASS",
            f"Tested {len(chars)} single characters across all parsers & detector without crash.",
        )
    else:
        report(
            "Scenario 2.1: Single character inputs",
            "FAIL",
            f"Crashes on characters: {single_char_crashes}",
        )

    # -------------------------------------------------------------------------
    # Scenario 3: Long paragraphs & extreme lengths
    # -------------------------------------------------------------------------
    try:
        long_line = _line(
            "Software Engineer " + ("developed scalable distributed systems " * 250),
            "p1-l1",
        )
        b_long = reconstruct_blocks("experience", [long_line])
        report(
            "Scenario 3.1: 5000-character single line",
            "PASS",
            f"Parsed into {len(b_long)} block(s) without timeout or regex backtracking crash.",
        )
    except Exception as e:
        report("Scenario 3.1: 5000-character single line", "FAIL", f"Crash: {e}")

    try:
        pipe_line = _line(
            "Title | " + " | ".join([f"Meta{i}" for i in range(50)]), "p1-l1"
        )
        b_pipe = reconstruct_blocks("experience", [pipe_line])
        report(
            "Scenario 3.2: Line with 50 pipe delimiters",
            "PASS",
            f"Parsed safely into {len(b_pipe)} block(s).",
        )
    except Exception as e:
        report("Scenario 3.2: Line with 50 pipe delimiters", "FAIL", f"Crash: {e}")

    try:
        long_skill_line = _line(
            "Skills: " + ", ".join([f"Skill{i}" for i in range(1000)]), "p1-l1"
        )
        b_skill = reconstruct_blocks("skills", [long_skill_line])
        report(
            "Scenario 3.3: 5000-character skill line",
            "PASS",
            f"Parsed into {len(b_skill)} block(s).",
        )
    except Exception as e:
        report("Scenario 3.3: 5000-character skill line", "FAIL", f"Crash: {e}")

    # -------------------------------------------------------------------------
    # Scenario 4: Duplicate lines & line provenance corruption
    # -------------------------------------------------------------------------
    try:
        dup_lines = [
            _line("Backend Developer", "p1-l1"),
            _line("TechCorp", "p1-l2"),
            _line("2023 - 2024", "p1-l3"),
            _line("• Built RESTful APIs", "p1-l4"),
            _line("• Built RESTful APIs", "p1-l5"),
            _line("• Built RESTful APIs", "p1-l6"),
        ]
        b_dup = reconstruct_blocks("experience", dup_lines)
        if b_dup:
            entry = b_dup[0]
            claimed = set(entry.source_line_ids)
            expected = {"p1-l1", "p1-l2", "p1-l3", "p1-l4", "p1-l5", "p1-l6"}
            missing = expected - claimed
            if not missing:
                report(
                    "Scenario 4.1: Duplicate bullet line provenance within single entry",
                    "PASS",
                    f"All duplicate bullet line IDs claimed: {entry.source_line_ids}",
                )
            else:
                report(
                    "Scenario 4.1: Duplicate bullet line provenance within single entry",
                    "FAIL",
                    f"Missing line IDs: {missing}. Claimed: {claimed}",
                )
    except Exception as e:
        report(
            "Scenario 4.1: Duplicate bullet line provenance within single entry",
            "FAIL",
            f"Crash: {e}",
        )

    try:
        dup_separate_lines = [
            _line("• Built RESTful APIs", "p1-l10"),
            _line("• Built RESTful APIs", "p1-l11"),
            _line("• Built RESTful APIs", "p1-l12"),
        ]
        b_dup_sep = reconstruct_blocks("activities", dup_separate_lines)
        b0_ids = b_dup_sep[0].source_line_ids if len(b_dup_sep) > 0 else []
        b1_ids = b_dup_sep[1].source_line_ids if len(b_dup_sep) > 1 else []
        b2_ids = b_dup_sep[2].source_line_ids if len(b_dup_sep) > 2 else []

        warnings0 = b_dup_sep[0].reconstruction_warnings if len(b_dup_sep) > 0 else []
        warnings1 = b_dup_sep[1].reconstruction_warnings if len(b_dup_sep) > 1 else []
        warnings2 = b_dup_sep[2].reconstruction_warnings if len(b_dup_sep) > 2 else []

        if (
            len(b_dup_sep) == 3
            and b0_ids == ["p1-l10"]
            and b1_ids == ["p1-l11"]
            and b2_ids == ["p1-l12"]
        ):
            report(
                "Scenario 4.2: Duplicate separate paragraph blocks provenance",
                "PASS",
                "Each duplicate block cleanly claimed its exact line ID.",
            )
        else:
            report(
                "Scenario 4.2: Duplicate separate paragraph blocks provenance",
                "FAIL",
                f"PROVENANCE CORRUPTION CONFIRMED! Block 0 claimed {b0_ids} (warnings: {warnings0}), "
                f"Block 1 claimed {b1_ids} (warnings: {warnings1}), "
                f"Block 2 claimed {b2_ids} (warnings: {warnings2}).",
            )
    except Exception as e:
        report(
            "Scenario 4.2: Duplicate separate paragraph blocks provenance",
            "FAIL",
            f"Crash: {e}",
        )

    # Substring provenance test
    try:
        sub_lines = [
            _line("Java", "p1-l20"),
        ]
        sg1 = CVSkillGroupBlock(label="Languages", skills=["JavaScript", "Java"])
        claimed_ids = set()
        attach_reconstruction_metadata(
            [sg1], sub_lines, "skills", claimed_line_ids=claimed_ids
        )
        if "p1-l20" in sg1.source_line_ids:
            report(
                "Scenario 4.3: Substring line matching (Java vs JavaScript)",
                "WARN",
                f"Line 'Java' matched block with 'JavaScript' via substring overlap. Claimed IDs: {sg1.source_line_ids}",
            )
        else:
            report(
                "Scenario 4.3: Substring line matching (Java vs JavaScript)",
                "PASS",
                "Did not over-claim line.",
            )
    except Exception as e:
        report("Scenario 4.3: Substring line matching", "FAIL", f"Crash: {e}")

    # -------------------------------------------------------------------------
    # Scenario 5: Vietnamese diacritics & Unicode
    # -------------------------------------------------------------------------
    try:
        vn_lines = [
            _line("Kỹ sư Lập trình Backend", "p1-l1"),
            _line("Tập đoàn Công nghệ FPT", "p1-l2"),
            _line("Tháng 01/2022 – Hiện tại", "p1-l3"),
            _line(
                "• Phát triển hệ thống microservices sử dụng Python và FastAPI", "p1-l4"
            ),
        ]
        b_vn = reconstruct_blocks("experience", vn_lines)
        if b_vn and isinstance(b_vn[0], CVEntryBlock):
            entry = b_vn[0]
            if (
                entry.title == "Kỹ sư Lập trình Backend"
                and entry.organization == "Tập đoàn Công nghệ FPT"
            ):
                report(
                    "Scenario 5.1: Vietnamese experience parsing",
                    "PASS",
                    f"Successfully parsed Vietnamese title and org: {entry.title=}, {entry.organization=}",
                )
            else:
                report(
                    "Scenario 5.1: Vietnamese experience parsing",
                    "WARN",
                    f"Incomplete fields: {entry.title=}, {entry.organization=}",
                )
        else:
            report(
                "Scenario 5.1: Vietnamese experience parsing",
                "FAIL",
                f"Failed to parse entry: {b_vn=}",
            )
    except Exception as e:
        report("Scenario 5.1: Vietnamese experience parsing", "FAIL", f"Crash: {e}")

    try:
        emoji_lines = [
            _line("💻 Backend Developer 🚀", "p1-l1"),
            _line("TechCorp Inc. 🏢", "p1-l2"),
            _line("• Built REST APIs 🔥", "p1-l3"),
        ]
        b_emoji = reconstruct_blocks("experience", emoji_lines)
        report(
            "Scenario 5.2: Emojis and special unicode symbols",
            "PASS",
            f"Parsed {len(b_emoji)} block(s) safely.",
        )
    except Exception as e:
        report(
            "Scenario 5.2: Emojis and special unicode symbols", "FAIL", f"Crash: {e}"
        )

    # -------------------------------------------------------------------------
    # Scenario 6: Unusual section headings
    # -------------------------------------------------------------------------
    headings = [
        ("WORK EXPERIENCE", "experience"),
        ("KINH NGHIỆM LÀM VIỆC", "experience"),
        ("WORK EXPERIENCE:", "experience"),
        ("1. WORK EXPERIENCE", "experience"),
        ("::: TECHNICAL SKILLS :::", "skills"),
        ("KỸ NĂNG & CÔNG NGHỆ", "skills"),
    ]
    for text, expected in headings:
        try:
            res = classify_heading(text)
            if res and res[0] == expected:
                report(
                    f"Scenario 6.1: Heading '{text}'", "PASS", f"Classified as {res[0]}"
                )
            elif res:
                report(
                    f"Scenario 6.1: Heading '{text}'",
                    "WARN",
                    f"Classified as {res[0]} (expected {expected})",
                )
            else:
                report(
                    f"Scenario 6.1: Heading '{text}'",
                    "WARN",
                    f"classify_heading returned None for variant '{text}'. Falls back to custom section in detector.",
                )
        except Exception as e:
            report(f"Scenario 6.1: Heading '{text}'", "FAIL", f"Crash: {e}")

    try:
        very_long_heading = (
            "THIS IS A VERY LONG LINE THAT CONTAINS FIFTY WORDS AND SHOULD DEFINITELY NOT BE CLASSIFIED AS A SECTION HEADING BY THE DETECTOR PIPELINE BECAUSE HEADINGS ARE SHORT "
            * 3
        )
        long_h_line = _line(very_long_heading, "p1-l1", font_size=16.0, font_weight=700)
        doc_long_h = detect_sections([long_h_line])
        if (
            len(doc_long_h.sections) == 1
            and doc_long_h.sections[0].type == "custom"
            and doc_long_h.sections[0].title == "Unclassified Content"
        ):
            report(
                "Scenario 6.2: 50-word heading line",
                "PASS",
                "Rejected 50-word line as section heading. Put in Unclassified Content.",
            )
        else:
            report(
                "Scenario 6.2: 50-word heading line",
                "WARN",
                f"Unexpected sections: {[s.title for s in doc_long_h.sections]}",
            )
    except Exception as e:
        report("Scenario 6.2: 50-word heading line", "FAIL", f"Crash: {e}")

    print("\n======================================================================")
    print("EMPIRICAL HARNESS SUMMARY")
    print("======================================================================")
    passes = sum(1 for _, status, _ in results if status == "PASS")
    fails = sum(1 for _, status, _ in results if status == "FAIL")
    warns = sum(1 for _, status, _ in results if status == "WARN")
    print(
        f"TOTAL TESTS: {len(results)} | PASS: {passes} | FAIL: {fails} | WARN: {warns}\n"
    )


if __name__ == "__main__":
    run_empirical_harness()
