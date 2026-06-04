"""
Generate Vietnamese SEO blog posts as MDX files for daucv.com.

Cron-friendly usage:
    cd /path/to/cv-fit-app/backend
    ../.venv/bin/python3 scripts/generate_seo_blog_posts.py --min 2 --max 4
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import random
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, Field, model_validator

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
BLOG_DIR = PROJECT_DIR / "frontend" / "content" / "blog"
COVER_DIR = PROJECT_DIR / "frontend" / "public" / "blog"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


AUTHOR = "Bé Đậu"
AUTHOR_AVATAR = "https://ui-avatars.com/api/?name=Bé+Đậu&background=E8F5E9&color=2E7D32"
DEFAULT_CTA_HREF = "/app/setup"

COVER_THEMES = [
    ("#2F4F4F", "#5A9E40", "#F0F6DC"),
    ("#263F3F", "#4F8F5B", "#E8F5E9"),
    ("#254346", "#77A647", "#F7FAEF"),
    ("#31514A", "#6A9F3B", "#EEF7E8"),
    ("#243E3E", "#8AAF45", "#F4F8E8"),
    ("#36544B", "#5E9D6D", "#EDF7EE"),
]

SEO_CLUSTERS = [
    "CV chuẩn ATS cho sinh viên mới ra trường",
    "cách viết CV theo ngành nghề tại Việt Nam",
    "mẫu CV tiếng Việt chuyên nghiệp",
    "mẹo tối ưu CV bằng AI",
    "cách viết kinh nghiệm làm việc trong CV",
    "cách viết CV trái ngành",
    "chuẩn bị phỏng vấn xin việc",
    "lỗi phổ biến khiến CV bị loại",
    "CV cho thực tập sinh",
    "CV cho fresher IT",
    "CV marketing",
    "CV sales",
    "CV kế toán",
    "CV nhân sự",
    "CV chăm sóc khách hàng",
    "CV designer",
    "CV logistics",
    "CV data analyst",
    "CV product manager",
    "cover letter tiếng Việt",
    "portfolio và CV",
    "LinkedIn và CV",
    "từ khóa trong JD và CV",
    "đánh giá CV trước khi ứng tuyển",
]


def coerce_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("description") or item.get("content") or item.get("title")
                if isinstance(text, str) and text.strip():
                    items.append(text.strip())
        return items
    return []


def clip_text(value: object, fallback: str, max_length: int) -> str:
    text = str(value or fallback).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip(" .,;:-") + "…"


def first_value(data: dict, keys: list[str], fallback: object = "") -> object:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return fallback


class ArticleSection(BaseModel):
    title: str = Field(..., min_length=8, max_length=90)
    paragraphs: list[str] = Field(..., min_length=1, max_length=4)
    bullets: list[str] = Field(default_factory=list, max_length=6)

    @model_validator(mode="before")
    @classmethod
    def normalize_section(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        title = first_value(data, ["title", "heading", "header"], "Nội dung cần lưu ý")
        paragraphs = coerce_str_list(first_value(data, ["paragraphs", "content", "body", "description"], []))
        bullets = coerce_str_list(first_value(data, ["bullets", "bullet_points", "items", "tips"], []))
        if not paragraphs and bullets:
            paragraphs = [bullets.pop(0)]
        if not paragraphs:
            paragraphs = ["Phần này tập trung vào các điểm thực tế giúp người đọc tối ưu CV hiệu quả hơn."]

        data["title"] = clip_text(title, "Nội dung cần lưu ý", 90)
        data["paragraphs"] = [clip_text(item, item, 500) for item in paragraphs[:4]]
        data["bullets"] = [clip_text(item, item, 180) for item in bullets[:6]]
        return data


class FeatureItem(BaseModel):
    icon: str = Field(..., min_length=2, max_length=40)
    title: str = Field(..., min_length=4, max_length=50)
    description: str = Field(..., min_length=20, max_length=180)

    @model_validator(mode="before")
    @classmethod
    def normalize_feature(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        data["icon"] = clip_text(first_value(data, ["icon"], "CheckCircle2"), "CheckCircle2", 40)
        data["title"] = clip_text(first_value(data, ["title", "heading"], "Điểm cần tối ưu"), "Điểm cần tối ưu", 50)
        data["description"] = clip_text(
            first_value(data, ["description", "content", "text"], "Một điểm quan trọng giúp CV rõ ràng và thân thiện hơn với ATS."),
            "Một điểm quan trọng giúp CV rõ ràng và thân thiện hơn với ATS.",
            180,
        )
        return data


class StepItem(BaseModel):
    title: str = Field(..., min_length=4, max_length=70)
    description: str = Field(..., min_length=20, max_length=220)

    @model_validator(mode="before")
    @classmethod
    def normalize_step(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        data["title"] = clip_text(first_value(data, ["title", "heading"], "Bước tối ưu"), "Bước tối ưu", 70)
        data["description"] = clip_text(
            first_value(data, ["description", "content", "text"], "Thực hiện bước này để CV rõ ràng và sát hơn với vị trí ứng tuyển."),
            "Thực hiện bước này để CV rõ ràng và sát hơn với vị trí ứng tuyển.",
            220,
        )
        return data


class ArticleDraft(BaseModel):
    title: str = Field(..., min_length=25, max_length=90)
    description: str = Field(..., min_length=80, max_length=170)
    primary_keyword: str = Field(..., min_length=5, max_length=80)
    category: str = Field(..., min_length=3, max_length=40)
    tags: list[str] = Field(..., min_length=3, max_length=6)
    read_time: str = Field(..., min_length=5, max_length=20)
    intro: list[str] = Field(..., min_length=2, max_length=4)
    takeaways: list[str] = Field(..., min_length=3, max_length=5)
    feature_title: str = Field(..., min_length=8, max_length=80)
    features: list[FeatureItem] = Field(..., min_length=3, max_length=4)
    sections: list[ArticleSection] = Field(..., min_length=4, max_length=7)
    checklist_title: str = Field(..., min_length=8, max_length=80)
    checklist_items: list[str] = Field(..., min_length=4, max_length=8)
    steps_title: str = Field(..., min_length=8, max_length=80)
    steps: list[StepItem] = Field(..., min_length=3, max_length=5)
    cta_title: str = Field(..., min_length=8, max_length=80)
    cta_description: str = Field(..., min_length=30, max_length=180)

    @model_validator(mode="before")
    @classmethod
    def normalize_article(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        data = dict(value)
        title = clip_text(first_value(data, ["title", "headline"], "Cách viết CV chuẩn ATS cho người tìm việc"), "Cách viết CV chuẩn ATS cho người tìm việc", 90)
        description = clip_text(
            first_value(data, ["description", "meta_description", "summary"], "Hướng dẫn thực tế giúp bạn viết CV rõ ràng, chuẩn ATS và tăng cơ hội được nhà tuyển dụng phản hồi."),
            "Hướng dẫn thực tế giúp bạn viết CV rõ ràng, chuẩn ATS và tăng cơ hội được nhà tuyển dụng phản hồi.",
            170,
        )

        raw_sections = first_value(data, ["sections", "outline", "body_sections"], [])
        sections = raw_sections if isinstance(raw_sections, list) else []
        if len(sections) < 4:
            sections = [
                *sections,
                {"title": "Vì sao CV chuẩn ATS quan trọng", "paragraphs": ["CV chuẩn ATS giúp hệ thống tuyển dụng đọc đúng thông tin, từ đó tăng khả năng hồ sơ được chuyển đến nhà tuyển dụng thật."]},
                {"title": "Cách chọn từ khóa từ mô tả công việc", "paragraphs": ["Hãy đọc kỹ JD, chọn các kỹ năng và yêu cầu thật sự khớp với kinh nghiệm của bạn, rồi đưa vào CV bằng ngôn ngữ tự nhiên."]},
                {"title": "Những lỗi định dạng cần tránh", "paragraphs": ["Tránh dùng quá nhiều bảng, icon, ảnh và bố cục nhiều cột vì các yếu tố này có thể khiến ATS đọc sai nội dung."]},
                {"title": "Cách kiểm tra CV trước khi gửi", "paragraphs": ["Copy nội dung CV sang trình soạn thảo văn bản đơn giản để xem thứ tự thông tin có còn rõ ràng hay không."]},
            ][:4]

        intro = coerce_str_list(first_value(data, ["intro", "introduction", "opening"], []))
        if not intro:
            intro = [
                description,
                "Bài viết này giúp bạn hiểu cách tối ưu CV theo hướng thực tế, dễ đọc với cả ATS và nhà tuyển dụng.",
            ]

        tags = coerce_str_list(first_value(data, ["tags", "keywords"], []))
        if len(tags) < 3:
            tags = [*tags, "CV", "ATS", "Tìm việc"][:3]

        takeaways = coerce_str_list(first_value(data, ["takeaways", "key_takeaways", "learning_points"], []))
        if len(takeaways) < 3:
            takeaways = [
                "Biết cách nhận diện yêu cầu quan trọng trong mô tả công việc.",
                "Hiểu cách trình bày CV để ATS đọc đúng thông tin.",
                "Có checklist kiểm tra CV trước khi ứng tuyển.",
            ]

        features = first_value(data, ["features", "feature_items"], [])
        if not isinstance(features, list) or len(features) < 3:
            features = [
                {"icon": "ScanLine", "title": "Dễ đọc với ATS", "description": "Bố cục rõ ràng giúp hệ thống tuyển dụng nhận diện đúng thông tin chính trong CV."},
                {"icon": "Search", "title": "Đúng từ khóa", "description": "Từ khóa được chọn từ JD và đặt tự nhiên trong kinh nghiệm, kỹ năng và dự án."},
                {"icon": "CheckCircle2", "title": "Sẵn sàng ứng tuyển", "description": "Checklist cuối bài giúp bạn rà soát nhanh trước khi gửi hồ sơ."},
            ]

        steps = first_value(data, ["steps", "action_steps", "process"], [])
        if not isinstance(steps, list) or len(steps) < 3:
            steps = [
                {"title": "Đọc kỹ mô tả công việc", "description": "Gạch chân kỹ năng, công cụ, trách nhiệm và tiêu chí bắt buộc xuất hiện trong JD."},
                {"title": "So khớp với kinh nghiệm thật", "description": "Chỉ đưa vào CV những keyword bạn có thể chứng minh bằng dự án, kết quả hoặc trách nhiệm cụ thể."},
                {"title": "Kiểm tra định dạng", "description": "Đảm bảo CV copy được nội dung, tiêu đề rõ ràng và không phụ thuộc vào icon hoặc hình ảnh."},
            ]

        checklist_items = coerce_str_list(first_value(data, ["checklist_items", "checklist", "final_checklist"], []))
        if len(checklist_items) < 4:
            checklist_items = [
                "Tiêu đề các phần như Kinh nghiệm, Kỹ năng, Học vấn rõ ràng.",
                "Có từ khóa quan trọng từ JD nhưng không nhồi lặp.",
                "Mỗi kinh nghiệm có kết quả hoặc phạm vi công việc cụ thể.",
                "File PDF vẫn copy được nội dung theo đúng thứ tự.",
            ]

        data["title"] = title
        data["description"] = description
        data["primary_keyword"] = clip_text(first_value(data, ["primary_keyword", "keyword", "main_keyword"], tags[0]), tags[0], 80)
        data["category"] = clip_text(first_value(data, ["category"], "CV & Resumes"), "CV & Resumes", 40)
        data["tags"] = [clip_text(tag, tag, 30) for tag in tags[:6]]
        data["read_time"] = clip_text(first_value(data, ["read_time", "estimated_read_time"], "5 min read"), "5 min read", 20)
        data["intro"] = [clip_text(item, item, 500) for item in intro[:4]]
        data["takeaways"] = [clip_text(item, item, 180) for item in takeaways[:5]]
        data["feature_title"] = clip_text(first_value(data, ["feature_title"], "Những điểm cần tối ưu"), "Những điểm cần tối ưu", 80)
        data["features"] = features[:4]
        data["sections"] = sections[:7]
        data["checklist_title"] = clip_text(first_value(data, ["checklist_title"], "Checklist trước khi gửi CV"), "Checklist trước khi gửi CV", 80)
        data["checklist_items"] = [clip_text(item, item, 180) for item in checklist_items[:8]]
        data["steps_title"] = clip_text(first_value(data, ["steps_title"], "Các bước tối ưu CV"), "Các bước tối ưu CV", 80)
        data["steps"] = steps[:5]
        data["cta_title"] = clip_text(first_value(data, ["cta_title"], "Tối ưu CV của bạn với Đậu"), "Tối ưu CV của bạn với Đậu", 80)
        data["cta_description"] = clip_text(
            first_value(data, ["cta_description"], "Dùng Đậu để phân tích CV, tìm điểm cần cải thiện và chuẩn bị hồ sơ ứng tuyển tự tin hơn."),
            "Dùng Đậu để phân tích CV, tìm điểm cần cải thiện và chuẩn bị hồ sơ ứng tuyển tự tin hơn.",
            180,
        )
        return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Vietnamese SEO MDX blog posts.")
    parser.add_argument("--min", type=int, default=2, help="Minimum posts to generate.")
    parser.add_argument("--max", type=int, default=4, help="Maximum posts to generate.")
    parser.add_argument("--count", type=int, help="Exact number of posts to generate.")
    parser.add_argument("--dry-run", action="store_true", help="Generate and print metadata without writing files.")
    parser.add_argument("--topic", action="append", default=[], help="Optional topic seed. Can be repeated.")
    parser.add_argument("--date", help="Publish date in YYYY-MM-DD. Defaults to Asia/Ho_Chi_Minh today.")
    return parser.parse_args()


def load_existing_posts() -> list[dict[str, str]]:
    posts: list[dict[str, str]] = []
    if not BLOG_DIR.exists():
        return posts

    for path in sorted(BLOG_DIR.glob("*.mdx")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(text)
        posts.append(
            {
                "slug": path.stem,
                "title": str(frontmatter.get("title", path.stem)),
                "description": str(frontmatter.get("description", "")),
            }
        )
    return posts


def extract_frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    data = yaml.safe_load(match.group(1)) or {}
    return data if isinstance(data, dict) else {}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"(^-|-$)", "", value)[:90] or "bai-viet"


def unique_slug(title: str, existing_slugs: set[str]) -> str:
    base = slugify(title)
    slug = base
    counter = 2
    while slug in existing_slugs:
        slug = f"{base}-{counter}"
        counter += 1
    existing_slugs.add(slug)
    return slug


def cover_theme(slug: str) -> tuple[str, str, str]:
    digest = hashlib.sha256(slug.encode("utf-8")).digest()
    return COVER_THEMES[digest[0] % len(COVER_THEMES)]


def wrap_cover_title(title: str, max_chars: int = 26, max_lines: int = 4) -> list[str]:
    words = title.split()
    lines: list[str] = []
    current = ""
    consumed = 0
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            consumed += 1
            continue
        if current:
            lines.append(current)
        current = word
        consumed += 1
        if len(lines) == max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if consumed < len(words) and lines:
        lines[-1] = lines[-1].rstrip(" .,;:-") + "..."
    return lines


def render_cover_svg(article: ArticleDraft, slug: str) -> str:
    dark, green, light = cover_theme(slug)
    title_spans = "\n".join(
        f'<tspan x="82" y="{210 + index * 58}">{html.escape(line)}</tspan>'
        for index, line in enumerate(wrap_cover_title(article.title))
    )
    category = html.escape(article.category.upper())
    description = html.escape(article.description[:112].rstrip(" .,;:-"))
    accent = html.escape(article.tags[0] if article.tags else "CV chuẩn ATS")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(article.title)}</title>
  <desc id="desc">{html.escape(article.description)}</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{light}"/>
      <stop offset="1" stop-color="#FFFFFF"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#2F4F4F" flood-opacity="0.16"/>
    </filter>
  </defs>
  <rect width="1200" height="630" rx="44" fill="url(#bg)"/>
  <circle cx="1010" cy="116" r="154" fill="{green}" opacity="0.12"/>
  <circle cx="1066" cy="500" r="210" fill="{dark}" opacity="0.08"/>
  <rect x="66" y="58" width="1068" height="514" rx="38" fill="#FFFFFF" filter="url(#shadow)"/>
  <rect x="82" y="74" width="1036" height="482" rx="30" fill="{light}" opacity="0.48"/>
  <g transform="translate(82 106)">
    <rect width="208" height="42" rx="14" fill="#FFFFFF"/>
    <text x="18" y="28" fill="{green}" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700">{category}</text>
  </g>
  <text x="82" y="210" fill="{dark}" font-family="Arial, Helvetica, sans-serif" font-size="48" font-weight="800" letter-spacing="0">
    {title_spans}
  </text>
  <text x="82" y="482" fill="#5F6F55" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="500">
    <tspan x="82" y="482">{description}</tspan>
  </text>
  <g transform="translate(807 154)">
    <rect x="0" y="0" width="262" height="318" rx="24" fill="#FFFFFF" stroke="#DDEACF" stroke-width="3"/>
    <rect x="34" y="46" width="156" height="18" rx="9" fill="{dark}" opacity="0.78"/>
    <rect x="34" y="92" width="194" height="12" rx="6" fill="{green}" opacity="0.55"/>
    <rect x="34" y="124" width="174" height="12" rx="6" fill="{green}" opacity="0.36"/>
    <rect x="34" y="164" width="206" height="12" rx="6" fill="{dark}" opacity="0.22"/>
    <rect x="34" y="196" width="152" height="12" rx="6" fill="{dark}" opacity="0.18"/>
    <rect x="34" y="236" width="92" height="34" rx="12" fill="{green}" opacity="0.18"/>
    <path d="M218 42l34 34-78 80-34-34z" fill="{green}" opacity="0.9"/>
    <path d="M238 22l34 34-19 20-34-34z" fill="{dark}"/>
  </g>
  <g transform="translate(82 526)">
    <circle cx="20" cy="20" r="20" fill="#E8F5E9"/>
    <text x="20" y="27" text-anchor="middle" fill="{green}" font-family="Arial, Helvetica, sans-serif" font-size="16" font-weight="800">Đ</text>
    <text x="52" y="27" fill="{dark}" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="800">Đậu CV</text>
    <text x="190" y="27" fill="#6A7D69" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="600">- {accent}</text>
  </g>
</svg>
"""


def create_cover(article: ArticleDraft, slug: str) -> str:
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    cover_path = COVER_DIR / f"{slug}.svg"
    cover_path.write_text(render_cover_svg(article, slug), encoding="utf-8")
    return f"/blog/{slug}.svg"


def estimate_read_time(article: ArticleDraft) -> str:
    text_parts: list[str] = []
    text_parts.extend(article.intro)
    text_parts.extend(article.takeaways)
    for feature in article.features:
        text_parts.extend([feature.title, feature.description])
    for section in article.sections:
        text_parts.append(section.title)
        text_parts.extend(section.paragraphs)
        text_parts.extend(section.bullets)
    text_parts.extend(article.checklist_items)
    for step in article.steps:
        text_parts.extend([step.title, step.description])
    words = len(re.findall(r"\w+", " ".join(text_parts), re.UNICODE))
    minutes = max(4, round(words / 220))
    return f"{minutes} min read"


def yaml_list(items: Iterable[str]) -> str:
    return "[" + ", ".join(json.dumps(item, ensure_ascii=False) for item in items) + "]"


def js_array(items: Iterable[str], indent: str = "  ") -> str:
    body = ",\n".join(f'{indent}{json.dumps(item, ensure_ascii=False)}' for item in items)
    return "[\n" + body + "\n]"


def render_feature_grid(article: ArticleDraft) -> str:
    rows = []
    for feature in article.features:
        rows.append(
            "    { "
            f'icon: {json.dumps(feature.icon, ensure_ascii=False)}, '
            f'title: {json.dumps(feature.title, ensure_ascii=False)}, '
            f'description: {json.dumps(feature.description, ensure_ascii=False)}'
            " }"
        )
    return (
        "<FeatureGrid \n"
        f"  title={json.dumps(article.feature_title, ensure_ascii=False)}\n"
        "  features={[\n"
        + ",\n".join(rows)
        + "\n  ]} \n"
        "/>"
    )


def render_step_list(article: ArticleDraft) -> str:
    rows = []
    for step in article.steps:
        rows.append(
            "    { "
            f'title: {json.dumps(step.title, ensure_ascii=False)}, '
            f'description: {json.dumps(step.description, ensure_ascii=False)}'
            " }"
        )
    return (
        "<StepList \n"
        f"  title={json.dumps(article.steps_title, ensure_ascii=False)}\n"
        "  steps={[\n"
        + ",\n".join(rows)
        + "\n  ]} \n"
        "/>"
    )


def render_article(article: ArticleDraft, publish_date: str, cover_image: str) -> str:
    article.read_time = estimate_read_time(article)
    lines = [
        "---",
        f"title: {json.dumps(article.title, ensure_ascii=False)}",
        f"description: {json.dumps(article.description, ensure_ascii=False)}",
        f"date: {json.dumps(publish_date, ensure_ascii=False)}",
        f"category: {json.dumps(article.category, ensure_ascii=False)}",
        f"author: {json.dumps(AUTHOR, ensure_ascii=False)}",
        f"coverImage: {json.dumps(cover_image, ensure_ascii=False)}",
        f"readTime: {json.dumps(article.read_time, ensure_ascii=False)}",
        f"tags: {yaml_list(article.tags)}",
        f"authorAvatar: {json.dumps(AUTHOR_AVATAR, ensure_ascii=False)}",
        "---",
        "",
    ]

    for paragraph in article.intro:
        lines.extend([paragraph.strip(), ""])

    lines.extend(
        [
            "<TakeawaysBox takeaways={"
            + js_array(article.takeaways)
            + "} />",
            "",
            render_feature_grid(article),
            "",
        ]
    )

    midpoint = max(1, len(article.sections) // 2)
    for index, section in enumerate(article.sections):
        lines.extend([f"## {section.title.strip()}", ""])
        for paragraph in section.paragraphs:
            lines.extend([paragraph.strip(), ""])
        if section.bullets:
            lines.extend([*format_bullets(section.bullets), ""])
        if index == midpoint - 1:
            lines.extend([render_step_list(article), ""])

    lines.extend(
        [
            "<ChecklistSection ",
            f"  title={json.dumps(article.checklist_title, ensure_ascii=False)}",
            "  items={"
            + js_array(article.checklist_items)
            + "} ",
            "/>",
            "",
            "<BlogCTA ",
            f"  title={json.dumps(article.cta_title, ensure_ascii=False)}",
            f"  description={json.dumps(article.cta_description, ensure_ascii=False)}",
            '  buttonText="Thử Ngay"',
            f'  buttonHref="{DEFAULT_CTA_HREF}"',
            '  image="/trophy.webp"',
            "/>",
            "",
        ]
    )
    return "\n".join(lines)


def format_bullets(items: list[str]) -> list[str]:
    return [f"- {item.strip()}" for item in items]


def build_prompt(existing_posts: list[dict[str, str]], topic_seed: str, publish_date: str) -> tuple[str, str]:
    existing_summary = "\n".join(
        f"- {post['slug']}: {post['title']}" for post in existing_posts[-60:]
    )
    system_prompt = """
Bạn là senior SEO content strategist cho Đậu CV (daucv.com), một sản phẩm AI giúp người Việt phân tích CV, tối ưu CV chuẩn ATS, chuẩn bị phỏng vấn và viết nội dung ứng tuyển.

Nhiệm vụ: tạo một bài blog tiếng Việt evergreen, hữu ích, tự nhiên, không nhồi từ khóa, không bịa số liệu và không trích dẫn nguồn nếu không chắc. Bài viết phải phù hợp để xuất bản ở /blog trên daucv.com.

Chỉ trả JSON hợp lệ theo schema. Không dùng Markdown trong JSON ngoài nội dung paragraph/bullet thông thường. Không tạo frontmatter, import, HTML, JSX hoặc MDX component.
""".strip()

    user_prompt = f"""
Ngày xuất bản: {publish_date}
Seed chủ đề/keyword: {topic_seed}

Các bài đã có, tránh trùng title, slug, góc tiếp cận và outline:
{existing_summary or "- Chưa có nhiều bài."}

Yêu cầu nội dung:
- Viết cho người tìm việc tại Việt Nam, ưu tiên truy vấn dài bằng tiếng Việt.
- Tập trung vào CV, ATS, mẫu CV, phỏng vấn, AI career assistant hoặc tìm việc.
- Title nên chứa keyword chính, tự nhiên, dưới 90 ký tự.
- Description 120-160 ký tự, có giá trị SEO.
- Intro 2-4 đoạn ngắn.
- Sections có heading rõ ràng, mỗi section đủ chi tiết và thực tế.
- Bullet nên là lời khuyên hành động, không chung chung.
- Tags 3-6 tag ngắn.
- Feature icons chỉ dùng các tên lucide phổ biến: ScanLine, LayoutTemplate, Wand2, Zap, Search, FileText, CheckCircle2, Briefcase, GraduationCap, Target, MessageSquare.
- CTA hướng người đọc dùng Đậu để phân tích/tối ưu CV.
""".strip()
    return system_prompt, user_prompt


async def generate_one(existing_posts: list[dict[str, str]], topic_seed: str, publish_date: str) -> ArticleDraft:
    from app.core.config import PROVIDERS

    system_prompt, user_prompt = build_prompt(existing_posts, topic_seed, publish_date)
    last_error: Exception | None = None

    for provider in PROVIDERS:
        try:
            result = await provider.generate_structured(
                system_prompt=system_prompt,
                user_content=user_prompt,
                response_model=ArticleDraft,
                temperature=0.82,
            )
            return result.data
        except Exception as exc:
            last_error = exc
            print(f"[seo-blog] Provider {provider.name} failed: {exc}", file=sys.stderr)

    raise RuntimeError(f"All providers failed. Last error: {last_error}")


async def main() -> int:
    print("Starting generation...")
    args = parse_args()
    if args.count is not None:
        count = args.count
    else:
        count = random.randint(args.min, args.max)

    if count < 1:
        raise ValueError("count must be at least 1")

    publish_date = args.date or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        COVER_DIR.mkdir(parents=True, exist_ok=True)

    existing_posts = load_existing_posts()
    existing_slugs = {post["slug"] for post in existing_posts}
    topic_pool = args.topic[:] or random.sample(SEO_CLUSTERS, k=min(count, len(SEO_CLUSTERS)))

    created: list[dict[str, str]] = []
    for index in range(count):
        topic_seed = topic_pool[index % len(topic_pool)]
        article = await generate_one(existing_posts, topic_seed, publish_date)
        slug = unique_slug(article.title, existing_slugs)
        cover_image = f"/blog/{slug}.svg" if args.dry_run else create_cover(article, slug)
        output = render_article(article, publish_date, cover_image)
        output_path = BLOG_DIR / f"{slug}.mdx"

        if args.dry_run:
            print(f"[dry-run] {slug}: {article.title}")
        else:
            output_path.write_text(output, encoding="utf-8")
            print(f"[seo-blog] Created {output_path.relative_to(PROJECT_DIR)}")
            print(f"[seo-blog] Created frontend/public/blog/{slug}.svg")

        post_record = {
            "slug": slug,
            "title": article.title,
            "description": article.description,
            "coverImage": cover_image,
            "coverPath": f"frontend/public/blog/{slug}.svg",
        }
        existing_posts.append(post_record)
        created.append(post_record)

    print(json.dumps({"count": len(created), "posts": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
