"""Build a deterministic, privacy-safe Vietnamese CV/JD evaluation corpus.

The checked-in corpus contains fictional candidates and synthetic job
descriptions only.  Public job-board records must be collected separately and
their licence, terms, URL and collection time recorded before being added.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dataset" / "vietnamese_eval"


@dataclass(frozen=True)
class Role:
    key: str
    title: str
    family: str
    skills: tuple[str, ...]
    adjacent: str


ROLES = (
    Role(
        "backend",
        "Backend Developer",
        "software",
        ("Python", "FastAPI", "PostgreSQL", "Docker", "Git"),
        "Full-stack Developer",
    ),
    Role(
        "frontend",
        "Frontend Developer",
        "software",
        ("React", "TypeScript", "Next.js", "Tailwind CSS", "REST API"),
        "Full-stack Developer",
    ),
    Role(
        "data_engineer",
        "Data Engineer",
        "data",
        ("Python", "SQL", "Airflow", "Spark", "BigQuery"),
        "Data Analyst",
    ),
    Role(
        "data_analyst",
        "Data Analyst",
        "data",
        ("SQL", "Power BI", "Excel", "Python", "Statistics"),
        "Data Engineer",
    ),
    Role(
        "ai_engineer",
        "AI Engineer",
        "ai",
        ("Python", "PyTorch", "Machine Learning", "FastAPI", "Docker"),
        "Data Engineer",
    ),
    Role(
        "mlops",
        "MLOps Engineer",
        "ai",
        ("Python", "MLflow", "Kubernetes", "Docker", "AWS"),
        "AI Engineer",
    ),
    Role(
        "marketing",
        "Digital Marketing Executive",
        "marketing",
        ("SEO", "Google Ads", "Meta Ads", "GA4", "Content"),
        "Sales Executive",
    ),
    Role(
        "sales",
        "Sales Executive",
        "sales",
        ("CRM", "B2B Sales", "Negotiation", "Lead Generation", "Excel"),
        "Digital Marketing Executive",
    ),
    Role(
        "accountant",
        "Kế toán tổng hợp",
        "accounting",
        ("MISA", "Excel", "Thuế", "Báo cáo tài chính", "Hóa đơn"),
        "Financial Analyst",
    ),
    Role(
        "helpdesk",
        "IT Helpdesk",
        "it_support",
        ("Windows", "Microsoft 365", "Network", "Helpdesk", "Hardware"),
        "System Administrator",
    ),
)

NAMES = (
    "Nguyễn Minh Anh",
    "Trần Gia Hân",
    "Lê Quốc Huy",
    "Phạm Thu Hà",
    "Võ Hoàng Nam",
    "Đỗ Khánh Linh",
)
SCHOOLS = (
    "ĐH Bách Khoa TP.HCM",
    "ĐH Công nghệ Thông tin",
    "ĐH Kinh tế TP.HCM",
    "ĐH FPT",
    "ĐH Duy Tân",
    "ĐH Thương mại",
)
CITIES = ("TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng")
LEVELS = (
    ("fresher", 0.5),
    ("junior", 1.5),
    ("junior", 2.0),
    ("middle", 3.0),
    ("senior", 5.0),
    ("senior", 7.0),
)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def cv_text(
    role: Role, number: int, quality: str, name: str, level: str, years: float
) -> str:
    skills = list(role.skills)
    if quality == "weak":
        skills = skills[:2] + ["Excel", "Giao tiếp"]
        experience = "Hỗ trợ các công việc vận hành và học công cụ qua khóa học trực tuyến; chưa có dự án production."
        metric = "Mô tả còn chung chung, chưa nêu kết quả định lượng."
    elif quality == "average":
        experience = f"Tham gia phát triển sản phẩm liên quan đến {role.title}; phối hợp với team để xử lý yêu cầu và lỗi phát sinh."
        metric = (
            "Cải thiện thời gian xử lý công việc khoảng 15% trong một quy trình nội bộ."
        )
    else:
        experience = f"Phụ trách hạng mục {role.title} từ phân tích yêu cầu đến triển khai và theo dõi sau phát hành."
        metric = "Tự động hóa quy trình, giảm 30% thời gian xử lý và duy trì chất lượng theo KPI đã thống nhất."
    language_line = (
        "Tiếng Việt; đọc hiểu tài liệu tiếng Anh kỹ thuật."
        if number % 3
        else "Vietnamese native; English technical reading."
    )
    return f"""{name}
{role.title} | {level.title()} | {CITIES[number % len(CITIES)]}

TÓM TẮT
Ứng viên hư cấu phục vụ kiểm thử. Có {years:g} năm kinh nghiệm theo định hướng {role.title}.

KỸ NĂNG
{", ".join(skills)}

KINH NGHIỆM
202{number % 5}-2026 | Công ty hư cấu {role.family.title()} Lab
- {experience}
- {metric}

DỰ ÁN
- Dự án mô phỏng dùng {", ".join(skills[:3])}; có README, kiểm thử cơ bản và báo cáo kết quả.

HỌC VẤN
{SCHOOLS[number % len(SCHOOLS)]}

NGÔN NGỮ
{language_line}
"""


def jd_text(role: Role, number: int, level: str, years: float) -> str:
    required = ", ".join(role.skills[:3])
    preferred = ", ".join(role.skills[3:])
    return f"""{role.title} ({level.title()})

Công ty hư cấu {role.family.title()} Platform — {CITIES[number % len(CITIES)]}

MÔ TẢ CÔNG VIỆC
- Xây dựng và cải tiến sản phẩm thuộc nhóm {role.family} cho khách hàng tại Việt Nam.
- Phối hợp với Product, QA và các bên liên quan; theo dõi chất lượng sau triển khai.
- Viết tài liệu, báo cáo tiến độ và đề xuất cải tiến dựa trên dữ liệu.

YÊU CẦU
- Có từ {max(0, int(years - 1))}-{int(years + 1)} năm kinh nghiệm phù hợp.
- Bắt buộc: {required}.
- Ưu tiên: {preferred}.
- Giao tiếp rõ ràng, chủ động và đọc hiểu tài liệu chuyên môn.

Ghi chú: JD hư cấu phục vụ đánh giá mô hình; không phải tin tuyển dụng thật.
"""


def label_for(quality: str, same_role: bool) -> tuple[str, int]:
    if not same_role:
        return "unsuitable", 5
    return {
        "strong": ("strong", 90),
        "average": ("moderate", 65),
        "weak": ("weak", 35),
    }[quality]


def generate_dataset(root: Path = ROOT) -> None:
    base = root / "dataset" / "vietnamese_eval"
    cv_dir, jd_dir = base / "cvs" / "extracted_text", base / "jobs" / "cleaned_text"
    for directory in (
        cv_dir,
        jd_dir,
        base / "cvs" / "pdf",
        base / "jobs" / "raw_html",
        base / "pairs",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    cvs: list[dict[str, object]] = []
    for role_index, role in enumerate(ROLES):
        for variant, (level, years) in enumerate(LEVELS):
            number = role_index * len(LEVELS) + variant + 1
            quality = (
                "strong"
                if variant in (3, 4, 5)
                else "average"
                if variant in (1, 2)
                else "weak"
            )
            cv_id = f"cv_{number:04d}"
            filename = f"{cv_id}.txt"
            (cv_dir / filename).write_text(
                cv_text(role, number, quality, NAMES[variant], level, years),
                encoding="utf-8",
            )
            cvs.append(
                {
                    "cv_id": cv_id,
                    "text_path": f"cvs/extracted_text/{filename}",
                    "language": "vi" if variant % 3 else "mixed",
                    "target_role": role.title,
                    "role_key": role.key,
                    "seniority": level,
                    "years_experience": years,
                    "skills": list(role.skills),
                    "synthetic": True,
                    "contains_personal_data": False,
                    "expected_quality": quality,
                }
            )

    jds: list[dict[str, object]] = []
    for role_index, role in enumerate(ROLES):
        for variant in range(15):
            number = role_index * 15 + variant + 1
            level, years = LEVELS[variant % len(LEVELS)]
            jd_id = f"jd_{number:04d}"
            filename = f"{jd_id}.txt"
            (jd_dir / filename).write_text(
                jd_text(role, number, level, years), encoding="utf-8"
            )
            jds.append(
                {
                    "jd_id": jd_id,
                    "text_path": f"jobs/cleaned_text/{filename}",
                    "title": role.title,
                    "role_key": role.key,
                    "company": f"Fictional {role.family.title()} Platform",
                    "location": CITIES[number % len(CITIES)],
                    "seniority": level,
                    "required_skills": list(role.skills[:3]),
                    "preferred_skills": list(role.skills[3:]),
                    "source": "synthetic",
                    "source_url": None,
                    "collected_at": None,
                    "licence_reviewed": True,
                }
            )

    pairs: list[dict[str, object]] = []
    # 100 human-review queue, balanced across the four judgement labels.
    for index in range(100):
        target_label = ("strong", "moderate", "weak", "unsuitable")[index % 4]
        if target_label == "unsuitable":
            cv = cvs[index % len(cvs)]
            jd = next(j for j in jds if j["role_key"] != cv["role_key"])
            label, score = "unsuitable", 5
            rationale = "cross-family deliberate mismatch"
        else:
            quality = {"strong": "strong", "moderate": "average", "weak": "weak"}[
                target_label
            ]
            candidates = [cv for cv in cvs if cv["expected_quality"] == quality]
            cv = candidates[(index // 4) % len(candidates)]
            jd = next(j for j in jds if j["role_key"] == cv["role_key"])
            label, score = label_for(quality, True)
            rationale = "same-role quality band"
        pairs.append(
            {
                "pair_id": f"label_{index + 1:04d}",
                "cv_id": cv["cv_id"],
                "jd_id": jd["jd_id"],
                "split": "human_labelled",
                "expected_label": label,
                "expected_score": score,
                "human_label_status": "pending",
                "rationale": rationale,
            }
        )
    # 100 deliberate cross-family mismatches.
    for index in range(100):
        cv = cvs[index % len(cvs)]
        jd = next(
            j
            for j in jds
            if j["role_key"]
            not in (
                cv["role_key"],
                ROLES[index // 10].adjacent.lower().replace(" ", "_"),
            )
        )
        pairs.append(
            {
                "pair_id": f"mismatch_{index + 1:04d}",
                "cv_id": cv["cv_id"],
                "jd_id": jd["jd_id"],
                "split": "deliberate_mismatch",
                "expected_label": "unsuitable",
                "expected_score": 5,
                "human_label_status": "not_required",
                "rationale": "different role family and required skills",
            }
        )
    # 100 related-role pairs, intentionally not all direct matches.
    for index in range(100):
        role = ROLES[index % len(ROLES)]
        cv = next(c for c in cvs if c["role_key"] == role.key)
        adjacent_key = (
            role.adjacent.lower()
            .replace(" ", "_")
            .replace("kế_toán_tổng_hợp", "financial_analyst")
        )
        jd = next(
            (j for j in jds if j["role_key"] == adjacent_key),
            next(j for j in jds if j["role_key"] == role.key),
        )
        pairs.append(
            {
                "pair_id": f"related_{index + 1:04d}",
                "cv_id": cv["cv_id"],
                "jd_id": jd["jd_id"],
                "split": "closely_related",
                "expected_label": "moderate",
                "expected_score": 55,
                "human_label_status": "not_required",
                "rationale": "adjacent role; evaluate transferable skills versus missing core requirements",
            }
        )

    write_jsonl(base / "cvs" / "metadata.jsonl", cvs)
    write_jsonl(base / "jobs" / "metadata.jsonl", jds)
    fields = list(pairs[0])
    with (base / "pairs" / "evaluation_pairs.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(pairs)
    with (base / "sources.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["source", "base_url", "use", "status", "notes"]
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "source": "synthetic",
                    "base_url": "",
                    "use": "checked-in CVs and seed JDs",
                    "status": "ready",
                    "notes": "fictional; no candidate personal data",
                },
                {
                    "source": "ITviec",
                    "base_url": "https://itviec.com",
                    "use": "optional public-JD collection",
                    "status": "not_collected",
                    "notes": "review terms/robots and save URL/time/provenance",
                },
                {
                    "source": "TopCV",
                    "base_url": "https://www.topcv.vn",
                    "use": "layout research only",
                    "status": "not_collected",
                    "notes": "do not ingest candidate CVs",
                },
                {
                    "source": "Việc Làm 24h",
                    "base_url": "https://vieclam24h.vn",
                    "use": "layout research only",
                    "status": "not_collected",
                    "notes": "do not ingest candidate CVs",
                },
            ]
        )
    (base / "README.md").write_text(
        """# Vietnamese evaluation dataset\n\nGenerated, fictional Vietnamese CV/JD corpus for regression testing. It contains 60 CV texts, 150 seed JDs, and 300 labelled evaluation pairs. No PDFs or raw HTML are checked in: those directories are intentionally empty until a licensed, provenance-recorded collection is approved.\n\nRegenerate with `backend/venv/bin/python backend/scripts/generate_vietnamese_eval_dataset.py`. Pair labels are test expectations, not a substitute for independent human adjudication; `human_labelled` rows begin as `pending`.\n\nPublic-board policy: never collect candidate CVs; collect a job description only after checking the source terms/robots and store its original URL, collection time, source and licence/terms decision in `jobs/metadata.jsonl`.\n""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    generate_dataset()
