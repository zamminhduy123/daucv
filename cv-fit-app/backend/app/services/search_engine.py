"""
Search engine adapter — queries Serper API or Google CSE for site:domain jobs.

Used as the fallback data source (after Playwright crawler exhausts
its queries). When the crawler returns 0 results — e.g. due to
Cloudflare blocks, JS-heavy rendering, or stale selectors — this
provides an alternative via Google search results.
"""

import hashlib
import os
import re

from httpx import AsyncClient, Timeout

# Domain paths per source (for URL validation)
_DOMAIN_PATHS: dict[str, list[str | type]] = {
    "itviec": ["/it-jobs/", "/jobs/"],
    "topcv": ["/viec-lam/"],
    "glints": ["/opportunities/jobs/"],
    "jobsgo": ["/viec-lam/"],
    "vieclam24h": ["/viec-lam-", "/tuyen-dung-"],
    "vietnamworks": ["/viec-lam/", "/job/", re.compile(r"-\d+-jv$", re.I)],
    "ybox": ["/tuyen-dung/"],
    "careerviet": ["/tim-viec-lam/", re.compile(r"\.html$", re.I)],
}

# Skill dictionary for extraction
_SKILLS = [
    "python",
    "javascript",
    "typescript",
    "react",
    "reactjs",
    "next.js",
    "nextjs",
    "vue",
    "vuejs",
    "angular",
    "nodejs",
    "node.js",
    "express",
    "nestjs",
    "fastapi",
    "django",
    "flask",
    "spring",
    "spring boot",
    "java",
    "golang",
    "go",
    "php",
    "ruby",
    "rails",
    "swift",
    "kotlin",
    "flutter",
    "dart",
    "rust",
    "c++",
    "c#",
    "c",
    "sql",
    "mysql",
    "postgresql",
    "postgres",
    "mongodb",
    "nosql",
    "redis",
    "firebase",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "git",
    "gitlab",
    "github",
    "ci/cd",
    "jenkins",
    "terraform",
    "ansible",
    "machine learning",
    "deep learning",
    "ai",
    "nlp",
    "llm",
    "rag",
    "pytorch",
    "tensorflow",
    "figma",
    "ui/ux",
    "agile",
    "scrum",
    "jest",
    "cypress",
    "html",
    "css",
    "sass",
    "less",
    "tailwind",
    "bootstrap",
    "rest api",
    "graphql",
    "microservices",
    "serverless",
]

_CITIES: dict[str, str] = {
    "hồ chí minh": "Hồ Chí Minh",
    "ho chi minh": "Hồ Chí Minh",
    "hcm": "Hồ Chí Minh",
    "sài gòn": "Hồ Chí Minh",
    "saigon": "Hồ Chí Minh",
    "hà nội": "Hà Nội",
    "ha noi": "Hà Nội",
    "hn": "Hà Nội",
    "đà nẵng": "Đà Nẵng",
    "da nang": "Đà Nẵng",
    "dn": "Đà Nẵng",
}

_SENIORITY: dict[str, list[str]] = {
    "intern": ["intern", "thực tập", "thực tập sinh"],
    "fresher": ["fresher"],
    "junior": ["junior"],
    "middle": ["middle", "mid"],
    "senior": ["senior"],
}


def _is_job_url(url: str, source: str) -> bool:
    """Check if URL looks like a job listing."""
    from urllib.parse import urlparse

    path = urlparse(url).path.lower()
    patterns = _DOMAIN_PATHS.get(source, [])
    for p in patterns:
        if callable(p):
            if p.search(path):
                return True
        elif p in path:
            return True
    return False


def _infer_city(text: str) -> str | None:
    t = text.lower()
    for key, city in _CITIES.items():
        if key in t:
            return city
    return None


def _infer_salary(text: str) -> str | None:
    for pat in [
        r"(\d[\d\s.,-]+\s*(?:triệu|tr|trđ|usd|\$))",
        r"(up to \d+\s*(?:triệu|usd|\$))",
        r"(lên tới \d+\s*(?:triệu|usd|\$))",
        r"(cạnh tranh)",
        r"(thỏa thuận|thông thương)",
    ]:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).strip()
    return None


def _infer_level(text: str) -> str | None:
    t = text.lower()
    for level, kws in _SENIORITY.items():
        if any(kw in t for kw in kws):
            return level
    return None


def _extract_skills(text: str) -> list[str]:
    t = text.lower()
    found = []
    for skill in _SKILLS:
        escaped = skill.replace(" ", r"\s+")
        if re.search(escaped, t, re.I):
            found.append(skill.title())
    return found[:8]


def _parse_title_company(raw: str) -> tuple[str, str]:
    """Split 'Title | Company' style titles."""
    parts = re.split(r"\s*(?:\||[-–—@])\s*", raw, maxsplit=1)
    title = parts[0].strip()
    company = parts[1].strip() if len(parts) > 1 else "Không rõ công ty"
    # Clean Vietnamese prefixes
    title = re.sub(r"^(tuyển dụng|tuyển)\s+", "", title, flags=re.I).strip()
    title = title[0].upper() + title[1:] if title else title
    return title, company


async def search_via_engine(query: str, domain: str, limit: int = 4) -> list[dict]:
    """Search via Serper API or Google CSE.

    Returns list of job dicts matching JobResult schema.
    """
    search_query = f"site:{domain} {query}"

    serper_key = os.environ.get("SERPER_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")
    google_cx = os.environ.get("GOOGLE_CSE_ID")

    hits = []

    async with AsyncClient(timeout=Timeout(10.0)) as client:
        if serper_key:
            try:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": serper_key,
                        "Content-Type": "application/json",
                    },
                    json={"q": search_query, "num": limit},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("organic", [])[:limit]:
                        title = item.get("title", "")
                        link = item.get("link") or item.get("url", "")
                        snippet = item.get("snippet", "")
                        if title and link:
                            hits.append(
                                {"title": title, "link": link, "snippet": snippet}
                            )
            except Exception:
                pass

        if not hits and google_key and google_cx:
            try:
                url = (
                    f"https://www.googleapis.com/customsearch/v1?"
                    f"key={google_key}&cx={google_cx}&q={query}&num={limit}"
                )
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", [])[:limit]:
                        title = item.get("title", "")
                        link = item.get("link", "")
                        snippet = item.get("snippet", "")
                        if title and link:
                            hits.append(
                                {"title": title, "link": link, "snippet": snippet}
                            )
            except Exception:
                pass

    if not hits:
        # No API key configured or search failed — return empty results.
        # Mock results were removed because they generated fake URLs that
        # fail URL validation and provide zero useful data.
        return []

    # Filter to job URLs only
    job_source = (
        domain.split("/")[-1].split(".")[-2] if "/" in domain else domain.split(".")[-2]
    )
    # Map domain to source label
    source_map = {
        "itviec.com": "itviec",
        "topcv.vn": "topcv",
        "glints.com": "glints",
        "jobsgo.vn": "jobsgo",
        "vieclam24h.vn": "vieclam24h",
        "vietnamworks.com": "vietnamworks",
        "ybox.vn": "ybox",
        "careerviet.vn": "careerviet",
    }
    source = source_map.get(domain, domain)

    results = []
    for hit in hits[:limit]:
        if not _is_job_url(hit["link"], source):
            continue
        title, company = _parse_title_company(hit["title"])
        full_text = hit["snippet"] + " " + hit["title"]
        location = _infer_city(full_text)
        salary = _infer_salary(full_text)
        level = _infer_level(hit["title"])
        skills = _extract_skills(full_text)

        results.append(
            {
                "id": f"se-{source}-{hashlib.md5((hit['link'] + str(len(results))).encode()).hexdigest()[:8]}",
                "source": source,
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "level": level,
                "skills": skills,
                "posted_text": "Hôm nay",
                "url": hit["link"],
                "description_snippet": hit["snippet"],
            }
        )

    return results


async def search_via_engine_for_source(
    source: str, query: str, domain: str, limit: int = 4
) -> list[dict]:
    """Convenience wrapper: search for a specific source."""
    return await search_via_engine(query, domain, limit)
