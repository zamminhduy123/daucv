"""
Generate Vietnamese SEO blog posts as MDX files for daucv.com.

Cron-friendly usage:
    cd /path/to/cv-fit-app/backend
    ../.venv/bin/python3 scripts/generate_seo_blog_posts.py --min 2 --max 4
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

import yaml
from pydantic import BaseModel, Field, model_validator

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
BLOG_DIR = PROJECT_DIR / "frontend" / "content" / "blog"
PUBLIC_BLOG_DIR = PROJECT_DIR / "frontend" / "public" / "blog"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


AUTHOR = "Bé Đậu"
AUTHOR_AVATAR = "https://ui-avatars.com/api/?name=Bé+Đậu&background=E8F5E9&color=2E7D32"
DEFAULT_CTA_HREF = "/app/setup"

BRAND_PALETTES = [
    {
        "name": "ats",
        "eyebrow": "ATS • Keyword • Layout",
        "bg_start": "#EEF7E8",
        "bg_end": "#F9FFF6",
        "accent": "#5A9E40",
        "accent_soft": "#A8C99A",
        "ink": "#1F3B2F",
        "panel": "#FFFFFF",
        "pattern": "scan",
    },
    {
        "name": "interview",
        "eyebrow": "Interview • Storytelling • Confidence",
        "bg_start": "#F3F8EA",
        "bg_end": "#FFFDF7",
        "accent": "#3F8F6B",
        "accent_soft": "#BCD8AA",
        "ink": "#223A33",
        "panel": "#FFFDF8",
        "pattern": "dialog",
    },
    {
        "name": "career",
        "eyebrow": "Career • Growth • Positioning",
        "bg_start": "#ECF6F0",
        "bg_end": "#F7FCFF",
        "accent": "#4B8B78",
        "accent_soft": "#A6D2C6",
        "ink": "#1E3A36",
        "panel": "#FFFFFF",
        "pattern": "path",
    },
    {
        "name": "ai",
        "eyebrow": "AI • Optimisation • Workflow",
        "bg_start": "#EEF7F1",
        "bg_end": "#FCFFFB",
        "accent": "#2F7D57",
        "accent_soft": "#9ED3B4",
        "ink": "#1D342C",
        "panel": "#FFFFFF",
        "pattern": "spark",
    },
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


def choose_palette(article: ArticleDraft) -> dict[str, str]:
    haystack = " ".join(
        [
            article.title,
            article.primary_keyword,
            article.category,
            *article.tags,
        ]
    ).lower()
    if any(keyword in haystack for keyword in ("phỏng vấn", "interview", "cover letter", "linkedin")):
        return BRAND_PALETTES[1]
    if any(keyword in haystack for keyword in ("ai", "ats", "keyword", "fresher it", "data")):
        return BRAND_PALETTES[0] if "ai" not in haystack else BRAND_PALETTES[3]
    if any(keyword in haystack for keyword in ("manager", "sales", "marketing", "logistics", "kế toán", "nhân sự")):
        return BRAND_PALETTES[2]
    return BRAND_PALETTES[0]


def wrap_svg_text(text: str, max_chars: int = 28, max_lines: int = 3) -> list[str]:
    words = text.split()
    if not words:
        return ["Đậu CV"]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)

    if len(lines) <= max_lines:
        return lines

    collapsed = lines[: max_lines - 1]
    tail = " ".join(lines[max_lines - 1 :]).strip()
    if len(tail) > max_chars - 1:
        tail = tail[: max_chars - 1].rstrip(" .,;:-") + "…"
    collapsed.append(tail)
    return collapsed


def pattern_markup(pattern: str, accent: str, accent_soft: str, ink: str) -> str:
    if pattern == "dialog":
        return f"""
<g transform="translate(830 110)">
  <rect x="0" y="0" width="274" height="188" rx="32" fill="{accent}" opacity="0.14"/>
  <rect x="24" y="34" width="178" height="78" rx="28" fill="{accent}" opacity="0.94"/>
  <rect x="86" y="122" width="164" height="72" rx="28" fill="{accent_soft}" opacity="0.9"/>
  <circle cx="56" cy="72" r="8" fill="#FFFFFF"/>
  <circle cx="86" cy="72" r="8" fill="#FFFFFF"/>
  <circle cx="116" cy="72" r="8" fill="#FFFFFF"/>
</g>"""
    if pattern == "path":
        return f"""
<g transform="translate(824 102)">
  <rect x="0" y="0" width="280" height="300" rx="36" fill="{ink}" opacity="0.08"/>
  <path d="M38 246 C88 154 136 188 174 106 C194 62 230 42 252 54" stroke="{accent}" stroke-width="18" fill="none" stroke-linecap="round"/>
  <circle cx="38" cy="246" r="18" fill="{accent_soft}"/>
  <circle cx="174" cy="106" r="18" fill="{accent}" opacity="0.92"/>
  <circle cx="252" cy="54" r="18" fill="{ink}" opacity="0.8"/>
  <rect x="38" y="56" width="86" height="18" rx="9" fill="{accent_soft}"/>
  <rect x="38" y="86" width="128" height="18" rx="9" fill="{accent_soft}" opacity="0.72"/>
</g>"""
    if pattern == "spark":
        return f"""
<g transform="translate(844 108)">
  <rect x="0" y="0" width="248" height="300" rx="34" fill="{accent}" opacity="0.08"/>
  <path d="M120 32 L138 90 L196 108 L142 130 L126 188 L104 132 L46 116 L100 92 Z" fill="{accent}" opacity="0.96"/>
  <circle cx="58" cy="226" r="22" fill="{accent_soft}" opacity="0.9"/>
  <circle cx="188" cy="238" r="14" fill="{ink}" opacity="0.18"/>
  <rect x="40" y="248" width="160" height="16" rx="8" fill="{ink}" opacity="0.12"/>
  <rect x="40" y="274" width="116" height="16" rx="8" fill="{ink}" opacity="0.08"/>
</g>"""
    return f"""
<g transform="translate(834 110)">
  <rect x="0" y="0" width="256" height="308" rx="34" fill="{accent}" opacity="0.08"/>
  <rect x="28" y="42" width="196" height="30" rx="15" fill="{accent_soft}" opacity="0.95"/>
  <rect x="28" y="92" width="196" height="18" rx="9" fill="{ink}" opacity="0.12"/>
  <rect x="28" y="124" width="156" height="18" rx="9" fill="{ink}" opacity="0.12"/>
  <rect x="28" y="176" width="88" height="88" rx="22" fill="{accent}" opacity="0.9"/>
  <rect x="136" y="176" width="88" height="88" rx="22" fill="{accent_soft}" opacity="0.88"/>
  <path d="M52 220 H92" stroke="#FFFFFF" stroke-width="14" stroke-linecap="round"/>
  <path d="M72 200 V240" stroke="#FFFFFF" stroke-width="14" stroke-linecap="round"/>
</g>"""


def render_cover_svg(article: ArticleDraft, slug: str) -> str:
    palette = choose_palette(article)
    title_lines = wrap_svg_text(article.title)
    title_y = 196
    title_markup = []
    for index, line in enumerate(title_lines):
        title_markup.append(
            f'<text x="92" y="{title_y + index * 62}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="50" font-weight="700" fill="{palette["ink"]}">{escape(line)}</text>'
        )

    keyword = escape(article.primary_keyword[:44].rstrip())
    category = escape(article.category)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
<title>{escape(article.title)}</title>
<desc>Branded DauCV blog cover for {escape(article.title)}</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{palette["bg_start"]}"/>
    <stop offset="100%" stop-color="{palette["bg_end"]}"/>
  </linearGradient>
  <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{palette["panel"]}" stop-opacity="0.98"/>
    <stop offset="100%" stop-color="{palette["bg_start"]}" stop-opacity="0.9"/>
  </linearGradient>
</defs>
<rect width="1200" height="630" rx="36" fill="url(#bg)"/>
<circle cx="1084" cy="88" r="160" fill="{palette["accent_soft"]}" opacity="0.24"/>
<circle cx="1014" cy="556" r="146" fill="{palette["accent"]}" opacity="0.12"/>
<circle cx="86" cy="550" r="110" fill="{palette["accent_soft"]}" opacity="0.14"/>
<rect x="58" y="58" width="1084" height="514" rx="34" fill="url(#panel)" stroke="{palette["accent"]}" stroke-opacity="0.16"/>
<rect x="92" y="84" width="282" height="42" rx="21" fill="{palette["accent"]}"/>
<text x="124" y="112" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" fill="#FFFFFF">Đậu CV Blog</text>
<text x="92" y="154" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="600" fill="{palette["accent"]}">{escape(palette["eyebrow"])}</text>
{''.join(title_markup)}
<rect x="92" y="444" width="396" height="54" rx="27" fill="{palette["panel"]}" stroke="{palette["accent"]}" stroke-width="2"/>
<text x="122" y="479" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="{palette["accent"]}">{keyword}</text>
<rect x="92" y="514" width="226" height="46" rx="23" fill="{palette["ink"]}"/>
<text x="122" y="544" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" fill="#FFFFFF">daucv.com/blog</text>
<text x="92" y="590" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="500" fill="{palette["ink"]}" opacity="0.72">{category} • Tối ưu CV • Tăng cơ hội phỏng vấn</text>
{pattern_markup(palette["pattern"], palette["accent"], palette["accent_soft"], palette["ink"])}
</svg>
"""


def write_cover_image(article: ArticleDraft, slug: str) -> str:
    PUBLIC_BLOG_DIR.mkdir(parents=True, exist_ok=True)
    cover_filename = f"{slug}.svg"
    cover_path = PUBLIC_BLOG_DIR / cover_filename
    cover_path.write_text(render_cover_svg(article, slug), encoding="utf-8")
    return f"/blog/{cover_filename}"


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


def infer_category(topic_seed: str) -> str:
    topic = topic_seed.lower()
    if "phỏng vấn" in topic:
        return "Phỏng vấn"
    if "cover letter" in topic:
        return "Cover Letter"
    if "linkedin" in topic:
        return "LinkedIn"
    if "ats" in topic:
        return "ATS CV"
    if "ai" in topic:
        return "AI Career"
    if "thực tập" in topic or "fresher" in topic or "sinh viên" in topic:
        return "CV Fresher"
    return "CV & Resumes"


def fallback_title(topic_seed: str) -> str:
    mapping = {
        "CV chuẩn ATS cho sinh viên mới ra trường": "CV chuẩn ATS cho sinh viên mới ra trường: cách viết để dễ được gọi phỏng vấn",
        "cách viết CV theo ngành nghề tại Việt Nam": "Cách viết CV theo ngành nghề tại Việt Nam: chọn đúng điểm mạnh để nổi bật",
        "mẫu CV tiếng Việt chuyên nghiệp": "Mẫu CV tiếng Việt chuyên nghiệp: bố cục gọn, dễ đọc và thuyết phục",
        "mẹo tối ưu CV bằng AI": "Mẹo tối ưu CV bằng AI: cách dùng công cụ đúng để tăng chất lượng hồ sơ",
        "cách viết kinh nghiệm làm việc trong CV": "Cách viết kinh nghiệm làm việc trong CV: ngắn gọn nhưng vẫn có sức nặng",
        "cách viết CV trái ngành": "Cách viết CV trái ngành: nhấn đúng kỹ năng để nhà tuyển dụng vẫn muốn gặp bạn",
        "chuẩn bị phỏng vấn xin việc": "Chuẩn bị phỏng vấn xin việc: checklist giúp bạn nói rõ giá trị của mình",
        "lỗi phổ biến khiến CV bị loại": "Lỗi phổ biến khiến CV bị loại: 9 điểm nhỏ nhưng làm giảm mạnh cơ hội ứng tuyển",
        "CV cho thực tập sinh": "CV cho thực tập sinh: cách viết ít kinh nghiệm nhưng vẫn đủ thuyết phục",
        "CV cho fresher IT": "CV cho fresher IT: cách chọn dự án và kỹ năng để không bị chìm giữa nhiều hồ sơ",
        "CV marketing": "CV marketing: cách viết thành tích chiến dịch để nhà tuyển dụng nhìn thấy năng lực thật",
        "CV sales": "CV sales: cách viết kinh nghiệm bán hàng để thể hiện rõ kết quả và độ bền bỉ",
        "CV kế toán": "CV kế toán: cách trình bày kinh nghiệm, chứng từ và độ chính xác một cách thuyết phục",
        "CV nhân sự": "CV nhân sự: cách nhấn mạnh tuyển dụng, C&B và phối hợp nội bộ trong hồ sơ",
        "CV chăm sóc khách hàng": "CV chăm sóc khách hàng: cách viết CV cho vị trí CSKH rõ kỹ năng và chỉ số phục vụ",
        "CV designer": "CV designer: cách kết hợp portfolio và CV để nhà tuyển dụng thấy được gu lẫn năng lực",
        "CV logistics": "CV logistics: cách viết CV nêu bật vận hành, điều phối và kiểm soát tiến độ",
        "CV data analyst": "CV data analyst: cách viết CV nêu rõ tư duy phân tích, dashboard và tác động kinh doanh",
        "CV product manager": "CV product manager: cách viết CV thể hiện ưu tiên sản phẩm và phối hợp liên phòng ban",
        "cover letter tiếng Việt": "Cover letter tiếng Việt: mẫu viết ngắn gọn nhưng đủ để HR muốn đọc tiếp CV",
        "portfolio và CV": "Portfolio và CV khác nhau thế nào: cách dùng cả hai để tăng cơ hội phỏng vấn",
        "LinkedIn và CV": "LinkedIn và CV khác nhau thế nào: cách đồng bộ hồ sơ để không mất điểm với recruiter",
        "từ khóa trong JD và CV": "Từ khóa trong JD và CV: cách chọn đúng keyword mà không biến hồ sơ thành máy móc",
        "đánh giá CV trước khi ứng tuyển": "Đánh giá CV trước khi ứng tuyển: checklist tự rà soát trong 15 phút",
    }
    return mapping.get(topic_seed, f"{topic_seed[:1].upper()}{topic_seed[1:]}: hướng dẫn thực tế để tăng cơ hội ứng tuyển")


def fallback_article(topic_seed: str) -> ArticleDraft:
    title = fallback_title(topic_seed)
    category = infer_category(topic_seed)
    primary_keyword = topic_seed
    description = (
        f"Hướng dẫn thực tế về {topic_seed} dành cho người tìm việc tại Việt Nam, giúp CV rõ ràng hơn, chuẩn ATS hơn và tăng cơ hội được mời phỏng vấn."
    )
    intro = [
        f"{topic_seed[:1].upper()}{topic_seed[1:]} là truy vấn rất sát với nhu cầu thật của người tìm việc, vì phần lớn ứng viên biết mình cần sửa CV nhưng chưa rõ nên bắt đầu từ đâu.",
        "Thay vì thêm thật nhiều từ khóa hoặc trang trí quá mức, bạn nên tập trung vào thông tin mà nhà tuyển dụng cần đọc nhanh: bối cảnh công việc, hành động bạn đã làm và kết quả có thể chứng minh.",
        "Bài viết này gom lại các bước tối ưu dễ áp dụng để bạn có thể chỉnh CV trong một buổi, sau đó tự tin hơn khi gửi hồ sơ cho từng vị trí cụ thể.",
    ]
    takeaways = [
        f"Biết cách tiếp cận {topic_seed} theo hướng thực tế thay vì viết chung chung.",
        "Có cấu trúc rõ ràng để chuyển kinh nghiệm sang ngôn ngữ phù hợp với recruiter và ATS.",
        "Có checklist cuối bài để tự rà soát hồ sơ trước khi ứng tuyển.",
    ]
    feature_title = "3 nguyên tắc giúp CV thuyết phục hơn"
    features = [
        FeatureItem(icon="ScanLine", title="Ưu tiên độ rõ ràng", description="Thông tin phải dễ đọc với cả ATS lẫn recruiter, tránh bố cục làm đẹp nhưng khó quét."),
        FeatureItem(icon="Target", title="Bám sát vị trí ứng tuyển", description="Mỗi kinh nghiệm và kỹ năng nên được chọn theo mục tiêu ứng tuyển thay vì kể dàn trải."),
        FeatureItem(icon="CheckCircle2", title="Dùng bằng chứng cụ thể", description="Chỉ số, phạm vi công việc và kết quả thực tế luôn mạnh hơn mô tả chung chung."),
    ]
    sections = [
        ArticleSection(
            title=f"Hiểu đúng mục tiêu của {topic_seed}",
            paragraphs=[
                f"Khi làm tốt phần {topic_seed}, mục tiêu không chỉ là 'đủ đẹp để nộp' mà là giúp người đọc hiểu rất nhanh bạn phù hợp ở điểm nào. Điều này đặc biệt quan trọng khi recruiter chỉ dành ít hơn một phút cho mỗi hồ sơ ở vòng đầu.",
                "Một CV hiệu quả luôn trả lời ba câu hỏi: bạn đã làm gì, bạn làm tốt đến mức nào và điều đó liên quan gì đến vị trí đang tuyển. Nếu thiếu một trong ba, hồ sơ sẽ dễ bị đánh giá là mơ hồ.",
            ],
            bullets=[
                "Xác định 2-3 yêu cầu quan trọng nhất trong JD trước khi chỉnh CV.",
                "Viết lại phần tóm tắt để phản ánh đúng mục tiêu ứng tuyển hiện tại.",
                "Loại bỏ các chi tiết không hỗ trợ cho vị trí bạn đang nhắm tới.",
            ],
        ),
        ArticleSection(
            title="Chọn nội dung nào để giữ lại và nội dung nào nên cắt",
            paragraphs=[
                "Nhiều CV bị loãng vì cố nhồi mọi trải nghiệm từng có. Thực tế, recruiter đánh giá cao khả năng chọn lọc hơn là liệt kê thật dài. Mỗi dòng bạn giữ lại nên phục vụ cho một luận điểm rõ ràng về năng lực.",
                "Nếu kinh nghiệm chưa nhiều, hãy thay thế bằng dự án, môn học, hoạt động hoặc thành quả cá nhân có liên quan. Điều quan trọng là nêu được trách nhiệm, công cụ đã dùng và kết quả bạn tạo ra.",
            ],
            bullets=[
                "Giữ lại các trải nghiệm gần nhất hoặc sát nhất với vị trí đang ứng tuyển.",
                "Cắt các mô tả chỉ kể nhiệm vụ mà không có tác động hoặc kết quả.",
                "Ưu tiên động từ mạnh như xây dựng, phân tích, tối ưu, phối hợp, triển khai.",
            ],
        ),
        ArticleSection(
            title="Viết kinh nghiệm theo hướng recruiter dễ quét",
            paragraphs=[
                "Mỗi kinh nghiệm nên bắt đầu bằng một bối cảnh ngắn để người đọc hiểu bạn làm trong môi trường nào, sau đó đi vào hành động và kết quả. Cấu trúc này giúp hồ sơ vừa dễ đọc vừa dễ so khớp với JD.",
                "Nếu có số liệu, hãy dùng vừa đủ để tăng độ tin cậy. Nếu chưa có số liệu chính xác, bạn vẫn có thể nêu quy mô công việc, tần suất hoặc phạm vi chịu trách nhiệm thay vì bỏ trống hoàn toàn phần kết quả.",
            ],
            bullets=[
                "Một bullet tốt thường chỉ nên chứa một ý chính.",
                "Đưa công cụ, nền tảng hoặc phương pháp vào đúng nơi bạn thật sự đã dùng.",
                "Tránh lặp lại cùng một cụm từ khóa ở nhiều dòng liên tiếp.",
            ],
        ),
        ArticleSection(
            title="Kiểm tra lại định dạng trước khi gửi",
            paragraphs=[
                "Một bản CV chuẩn nội dung nhưng định dạng rối vẫn có thể làm giảm mạnh tỷ lệ phản hồi. Hãy mở file ở nhiều thiết bị hoặc copy thử sang trình soạn thảo đơn giản để xem thứ tự thông tin có còn mạch lạc không.",
                "Đây cũng là bước nên dùng công cụ như Đậu để đối chiếu JD, kiểm tra độ rõ ràng của từng phần và phát hiện những đoạn đang quá chung chung so với yêu cầu tuyển dụng.",
            ],
            bullets=[
                "Tên file nên chuyên nghiệp và dễ nhận diện.",
                "Tiêu đề phần nên thống nhất, không dùng icon thay cho chữ.",
                "Xuất PDF sau khi đã kiểm tra lỗi chính tả và khoảng trắng.",
            ],
        ),
    ]
    checklist_items = [
        "Tiêu đề hồ sơ và phần tóm tắt đã khớp với vị trí đang ứng tuyển.",
        "Các bullet kinh nghiệm có hành động và kết quả, không chỉ mô tả nhiệm vụ.",
        "Từ khóa quan trọng xuất hiện tự nhiên trong kỹ năng, kinh nghiệm hoặc dự án.",
        "Bố cục dễ đọc trên PDF và không phụ thuộc vào bảng hay text box phức tạp.",
        "Email, số điện thoại, LinkedIn hoặc portfolio đã được kiểm tra lại.",
    ]
    steps = [
        StepItem(title="Đọc JD và khoanh vùng điểm khớp", description="Tìm 3-5 yêu cầu quan trọng nhất rồi đánh dấu những trải nghiệm có thể chứng minh chúng trong CV."),
        StepItem(title="Viết lại phần kinh nghiệm theo tác động", description="Chuyển các dòng mô tả nhiệm vụ thành bullet có bối cảnh, hành động và kết quả để recruiter hiểu nhanh giá trị của bạn."),
        StepItem(title="Rà soát bằng công cụ trước khi nộp", description="Dùng Đậu để kiểm tra độ khớp với JD, phát hiện chỗ thiếu từ khóa hoặc phần diễn đạt còn yếu trước khi gửi hồ sơ."),
    ]
    return ArticleDraft(
        title=title,
        description=description,
        primary_keyword=primary_keyword,
        category=category,
        tags=["CV", "Xin việc", topic_seed[:28]],
        read_time="5 min read",
        intro=intro,
        takeaways=takeaways,
        feature_title=feature_title,
        features=features,
        sections=sections,
        checklist_title="Checklist trước khi bạn bấm gửi CV",
        checklist_items=checklist_items,
        steps_title="Quy trình tối ưu nhanh trong một buổi",
        steps=steps,
        cta_title="Muốn biết CV của bạn đang yếu ở đâu?",
        cta_description="Dùng Đậu để phân tích CV theo JD, tìm điểm chưa rõ và nhận gợi ý chỉnh sửa trước khi ứng tuyển.",
    )


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

    print(f"[seo-blog] Falling back to offline template for topic: {topic_seed}", file=sys.stderr)
    return fallback_article(topic_seed)


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

    existing_posts = load_existing_posts()
    existing_slugs = {post["slug"] for post in existing_posts}
    topic_pool = args.topic[:] or random.sample(SEO_CLUSTERS, k=min(count, len(SEO_CLUSTERS)))

    created: list[dict[str, str]] = []
    for index in range(count):
        topic_seed = topic_pool[index % len(topic_pool)]
        article = await generate_one(existing_posts, topic_seed, publish_date)
        slug = unique_slug(article.title, existing_slugs)
        cover_image = write_cover_image(article, slug)
        output = render_article(article, publish_date, cover_image)
        output_path = BLOG_DIR / f"{slug}.mdx"

        if args.dry_run:
            print(f"[dry-run] {slug}: {article.title}")
        else:
            output_path.write_text(output, encoding="utf-8")
            print(f"[seo-blog] Created {output_path.relative_to(PROJECT_DIR)}")

        post_record = {
            "slug": slug,
            "title": article.title,
            "description": article.description,
            "coverImage": cover_image,
        }
        existing_posts.append(post_record)
        created.append(post_record)

    print(json.dumps({"count": len(created), "posts": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
