"""Job crawler service — Playwright-based scraping for Vietnamese job boards.

Crawlers are organized by source. Each returns a list of JobResult dicts.
Sources that are known to work without Playwright (CareerViet, Ybox) use
httpx directly; the rest use a shared async Playwright browser.
"""

import asyncio
import hashlib
import json
import re
from contextlib import asynccontextmanager, suppress
from typing import Any
from urllib.parse import urljoin, urlparse

from httpx import AsyncClient, Timeout
from playwright.async_api import BrowserContext, Page
from playwright.async_api import async_playwright as _playwright

# ---------------------------------------------------------------------------
# Domain → source label mapping
# ---------------------------------------------------------------------------
SOURCE_LABELS: dict[str, str] = {
    "itviec.com": "itviec",
    "topcv.vn": "topcv",
    "glints.com": "glints",
    "jobsgo.vn": "jobsgo",
    "vieclam24h.vn": "vieclam24h",
    "vietnamworks.com": "vietnamworks",
    "careerviet.vn": "careerviet",
    "ybox.vn": "ybox",
}

# ---------------------------------------------------------------------------
# Search URL templates per source
# ---------------------------------------------------------------------------
SEARCH_URLS: dict[str, str] = {
    "itviec": "https://itviec.com/it-jobs?q={query}&city={city}",
    "topcv": "https://topcv.vn/viec-lam-it?keyword={query}&location={city}",
    "glints": "https://glints.com/vn/opportunities/jobs?keyword={query}&city={city}",
    "jobsgo": "https://jobsgo.vn/viec-lam?q={query}&q2={query}&q3=&city={city}",
    "vieclam24h": "https://www.vieclam24h.vn/tim-kiem-viec-lam?q={query}&q1={city}",
    "vietnamworks": "https://www.vietnamworks.com/tim-viec-lam?keyword={query}",
    "careerviet": "https://careerviet.vn/tim-viec-lam.html?keyword={query}",
    "ybox": "https://ybox.vn/api/v1/post?search={query}&category=tuyen-dung&page=1",
}

# Fallback search URL (no location) for sources that need it
FALLBACK_SEARCH_URLS: dict[str, str] = {
    "itviec": "https://itviec.com/it-jobs?q={query}",
    "topcv": "https://topcv.vn/viec-lam-it?keyword={query}",
    "glints": "https://glints.com/vn/opportunities/jobs?keyword={query}",
    "jobsgo": "https://jobsgo.vn/viec-lam?q={query}",
    "vieclam24h": "https://www.vieclam24h.vn/tim-kiem-viec-lam?q={query}",
    "vietnamworks": "https://www.vietnamworks.com/tim-viec-lam?keyword={query}",
    "careerviet": "https://careerviet.vn/tim-viec-lam.html?keyword={query}",
    "ybox": "https://ybox.vn/api/v1/post?search={query}&category=tuyen-dung&page=1",
}

# Browser stealth headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ---------------------------------------------------------------------------
# Skill dictionary for extraction from job text
# ---------------------------------------------------------------------------
_SKILLS_LIST = [
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

_VIETNAMESE_CITIES = {
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
    "dn": "Đ Đà Nẵng",
}

_SENIORITY_KEYWORDS = {
    "intern": ["intern", "thực tập", "thực tập sinh"],
    "fresher": ["fresher"],
    "junior": ["junior"],
    "middle": ["middle", "mid"],
    "senior": ["senior"],
}

# ---------------------------------------------------------------------------
# URL pattern validation — filters out non-job pages
# ---------------------------------------------------------------------------
_JOB_URL_PATTERNS: dict[str, list[str]] = {
    "itviec": ["/it-jobs/", "/jobs/"],
    "topcv": ["/viec-lam/"],
    "glints": ["/opportunities/jobs/"],
    "jobsgo": ["/viec-lam/"],
    "vieclam24h": ["/viec-lam-", "/tuyen-dung-"],
    "vietnamworks": ["/viec-lam/", "/job/", re.compile(r"-\d+-jv$", re.IGNORECASE)],
    "ybox": ["/tuyen-dung/"],
    "careerviet": ["/tim-viec-lam/", re.compile(r"\.html$", re.IGNORECASE)],
}


def _is_job_url(url: str, source: str) -> bool:
    """Check if a URL looks like a real job listing page."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path.lower()

        patterns = _JOB_URL_PATTERNS.get(source, [])
        for pattern in patterns:
            if callable(pattern):
                if pattern.search(path):
                    return True
            elif pattern in path:
                return True
        return False
    except Exception:
        return False


# ===================================================================
# Browser manager — singleton-ish async context manager
# ===================================================================


class BrowserManager:
    """Manages a single Playwright instance and browser context."""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._context: BrowserContext | None = None
        self._locked = asyncio.Lock()
        self._initialized = False

    async def start(self) -> None:
        """Launch browser (singleton — safe to call multiple times)."""
        async with self._locked:
            if self._initialized:
                return
            pw_ctx = _playwright()
            self._playwright = await pw_ctx.__aenter__()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=HEADERS["User-Agent"],
                locale="vi-VN",
                timezone_id="Asia/Ho_Chi_Minh",
                bypass_csp=True,
            )
            # Hide webdriver flag
            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
            """)
            self._initialized = True

    async def stop(self) -> None:
        """Close browser."""
        async with self._locked:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.__aexit__(None, None, None)
            self._initialized = False

    async def new_page(self) -> Page:
        """Create a new page in the shared context."""
        if not self._initialized:
            await self.start()
        return await self._context.new_page()


# Global browser manager instance
_browser_mgr = BrowserManager()


@asynccontextmanager
async def managed_browser():
    """Context manager for a short-lived browser session."""
    try:
        await _browser_mgr.start()
    except Exception:
        # start() may have entered Playwright before Chromium launch failed.
        # Release that partial state so repeated Render requests do not leak
        # driver processes while the search-engine fallback is in use.
        with suppress(Exception):
            await _browser_mgr.stop()
        raise
    try:
        yield _browser_mgr
    finally:
        # Don't stop — browser persists across requests for performance
        pass


# ===================================================================
# Page navigation helper with stealth
# ===================================================================


async def _navigate(page: Page, url: str, timeout_ms: int = 15000) -> bool:
    """Navigate to URL with stealth. Returns True if content loaded."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # Wait briefly for dynamic content
        await asyncio.sleep(0.5)
        return True
    except Exception:
        pass
    try:
        await page.goto(url, wait_until="commit", timeout=timeout_ms)
        await asyncio.sleep(1)
        return True
    except Exception:
        return False


# ===================================================================
# Text extraction helpers
# ===================================================================


def _extract_text(page: Page, selector: str) -> str | None:
    """Extract text content from the first matching element."""
    try:
        el = page.query_selector(selector)
        if el:
            text = el.inner_text(timeout=3000).strip()
            return text if text else None
    except Exception:
        pass
    return None


def _extract_all_texts(page: Page, selector: str) -> list[str]:
    """Extract text from all matching elements."""
    try:
        els = page.query_selector_all(selector)
        return [
            e.inner_text(timeout=3000).strip()
            for e in els
            if e.inner_text(timeout=3000).strip()
        ]
    except Exception:
        return []


def _extract_attrs(page: Page, selector: str, attr: str) -> list[str]:
    """Extract attribute values from all matching elements."""
    try:
        els = page.query_selector_all(selector)
        return [
            e.get_attribute(attr, timeout=3000) or ""
            for e in els
            if (e.get_attribute(attr, timeout=3000))
        ]
    except Exception:
        return []


def _extract_links(page: Page, selector: str) -> list[tuple[str, str]]:
    """Extract (href, text) pairs from all matching anchor elements."""
    try:
        els = page.query_selector_all(selector)
        results = []
        for el in els:
            href = el.get_attribute("href", timeout=3000)
            text = el.inner_text(timeout=3000).strip()
            if href and text:
                results.append((href, text))
        return results
    except Exception:
        return []


def _safe_company_logo_url(raw_url: str | None, base_url: str) -> str | None:
    """Return a safe absolute remote image URL, or ``None`` when unavailable.

    Job boards commonly lazy-load company logos using relative ``src`` or
    ``data-src`` values. We intentionally accept HTTPS images from the job
    board's own domain only, so scraped markup cannot make a user's browser
    request an arbitrary or private-network host.
    """
    if not raw_url:
        return None

    candidate = raw_url.strip()
    if not candidate or candidate.startswith(("data:", "javascript:")):
        return None

    absolute_url = urljoin(base_url, candidate)
    parsed = urlparse(absolute_url)
    base_host = (urlparse(base_url).hostname or "").lower()
    trusted_root = base_host.removeprefix("www.")
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not host
        or not trusted_root
        or (host != trusted_root and not host.endswith(f".{trusted_root}"))
    ):
        return None
    return absolute_url


def _extract_company_logo(card: Any, base_url: str) -> str | None:
    """Extract a company logo already present in a job-search result card.

    This does not visit a company page or call a third-party logo service. It
    only uses an image the job board supplied with the listing, preserving the
    posting's provenance and avoiding additional scan latency.
    """
    selectors = (
        "[class*='company'] img, [class*='employer'] img, "
        "[class*='logo'] img, img[class*='company'], img[class*='logo']"
    )
    try:
        images = card.query_selector_all(selectors)
        for image in images:
            for attribute in ("src", "data-src", "data-original", "data-lazy-src"):
                logo_url = _safe_company_logo_url(
                    image.get_attribute(attribute, timeout=3000),
                    base_url,
                )
                if logo_url:
                    return logo_url

            srcset = image.get_attribute("srcset", timeout=3000)
            if srcset:
                first_candidate = srcset.split(",", 1)[0].strip().split(" ", 1)[0]
                logo_url = _safe_company_logo_url(first_candidate, base_url)
                if logo_url:
                    return logo_url
    except Exception:
        return None
    return None


def _clean_text(text: str) -> str:
    """Clean whitespace and normalize text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _infer_city(text: str) -> str | None:
    """Infer Vietnamese city from text."""
    t = text.lower()
    for key, city in _VIETNAMESE_CITIES.items():
        if key in t:
            return city
    return None


def _infer_salary(text: str) -> str | None:
    """Extract salary from text."""
    patterns = [
        r"(\d[\d\s.,-]+\s*(?:triệu|tr|trđ|usd|\$))",
        r"(up to \d+\s*(?:triệu|usd|\$))",
        r"(lên tới \d+\s*(?:triệu|usd|\$))",
        r"(cạnh tranh)",
        r"(thỏa thuận|thông thương)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _infer_level(text: str) -> str | None:
    """Infer seniority level from text."""
    t = text.lower()
    for level, keywords in _SENIORITY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return level
    return None


def _extract_skills(text: str) -> list[str]:
    """Extract known skills from text."""
    t = text.lower()
    found = []
    for skill in _SKILLS_LIST:
        escaped = skill.replace(" ", r"\s+")
        if re.search(escaped, t, re.IGNORECASE):
            found.append(skill.title())
    return found[:8]  # Limit extracted skills


# ===================================================================
# Source crawlers — Playwright-based
# ===================================================================


async def _crawl_itviec(page: Page, query: str, location: str) -> list[dict]:
    """Crawl ITviec search results."""
    city = location if location else ""
    url = SEARCH_URLS["itviec"].format(query=query, city=city)
    success = await _navigate(page, url)
    if not success:
        return []

    jobs = []
    cards = page.query_selector_all(
        "div.it-job-card, [class*='it-job-card'], article.job-card, [class*='job-card']",
    )
    if not cards:
        # Fallback: try any anchor with href containing /it-jobs/
        links = page.query_selector_all('a[href*="/it-jobs/"]')
        for a in links[:10]:
            href = a.get_attribute("href", timeout=3000) or ""
            text = a.inner_text(timeout=3000).strip()
            if text and _is_job_url(href, "itviec"):
                # Try to extract company/salary from surrounding text
                parent = a
                full_text = parent.inner_text(timeout=3000).strip()
                company = (
                    _extract_text(parent, "span[class*='company'], p[class*='company']")
                    or "Không rõ công ty"
                )
                salary = _infer_salary(full_text)
                loc = _infer_city(full_text)
                level = _infer_level(text)
                jobs.append(
                    {
                        "id": f"itviec-se-{hashlib.md5((href + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "itviec",
                        "title": _clean_text(text.split("\n")[0])
                        if text
                        else "Không rõ",
                        "company": company,
                        "location": loc,
                        "salary": salary,
                        "level": level,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else f"https://itviec.com{href}",
                        "description_snippet": None,
                    },
                )
        return jobs

    for card in cards[:10]:
        try:
            title_el = card.query_selector(
                "h2 a, h3 a, [class*='title'] a, a[class*='title']",
            )
            company_el = card.query_selector(
                "span[class*='company'], p[class*='company'], [class*='company-name']",
            )
            location_el = card.query_selector(
                "span[class*='location'], [class*='location'], [class*='city']",
            )
            salary_el = card.query_selector("span[class*='salary'], [class*='salary']")
            link_el = card.query_selector("a[href]")

            title = title_el.inner_text(timeout=3000).strip() if title_el else ""
            company = (
                company_el.inner_text(timeout=3000).strip()
                if company_el
                else "Không rõ công ty"
            )
            company_logo_url = _extract_company_logo(card, "https://itviec.com")
            location = (
                location_el.inner_text(timeout=3000).strip() if location_el else None
            )
            salary = salary_el.inner_text(timeout=3000).strip() if salary_el else None
            href = link_el.get_attribute("href", timeout=3000) if link_el else ""
            full_text = card.inner_text(timeout=3000).strip()

            if title:
                if location:
                    location = _infer_city(location) or location
                level = _infer_level(title)
                jobs.append(
                    {
                        "id": f"itviec-se-{hashlib.md5((href or title + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "itviec",
                        "title": _clean_text(title),
                        "company": company,
                        "company_logo_url": company_logo_url,
                        "location": location,
                        "salary": salary,
                        "level": level,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else (f"https://itviec.com{href}" if href else ""),
                        "description_snippet": _clean_text(full_text[:300])
                        if full_text
                        else None,
                    },
                )
        except Exception:
            continue

    return jobs


async def _crawl_topcv(page: Page, query: str, location: str) -> list[dict]:
    """Crawl TopCV search results."""
    city = location if location else ""
    url = SEARCH_URLS["topcv"].format(query=query, city=city)
    success = await _navigate(page, url)
    if not success:
        return []

    jobs = []
    # TopCV uses various card patterns
    cards = page.query_selector_all(
        "div.job-item, div.job-card, li.job-item, [class*='job-item'], [class*='job-card'], "
        "div.row.jobs-list, div.item-vacancy",
    )
    if not cards:
        return []

    for card in cards[:10]:
        try:
            title_el = card.query_selector(
                "h3 a, h4 a, .job-title a, a.job-title, [class*='title'] a",
            )
            company_el = card.query_selector(
                ".company-name, .company, a[class*='company']",
            )
            location_el = card.query_selector(
                ".location, .address, .place, [class*='location']",
            )
            salary_el = card.query_selector(".salary, [class*='salary']")
            link_el = card.query_selector("a[href]")

            title = _clean_text(title_el.inner_text(timeout=3000)) if title_el else ""
            company = (
                _clean_text(company_el.inner_text(timeout=3000))
                if company_el
                else "Không rõ công ty"
            )
            company_logo_url = _extract_company_logo(card, "https://topcv.vn")
            location = (
                location_el.inner_text(timeout=3000).strip() if location_el else None
            )
            salary = salary_el.inner_text(timeout=3000).strip() if salary_el else None
            href = link_el.get_attribute("href", timeout=3000) if link_el else ""
            full_text = card.inner_text(timeout=3000).strip()

            if title:
                location = _infer_city(location or full_text)
                level = _infer_level(title)
                jobs.append(
                    {
                        "id": f"topcv-se-{hashlib.md5((href or title + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "topcv",
                        "title": title,
                        "company": company,
                        "company_logo_url": company_logo_url,
                        "location": location,
                        "salary": salary,
                        "level": level,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else (f"https://topcv.vn{href}" if href else ""),
                        "description_snippet": _clean_text(full_text[:300])
                        if full_text
                        else None,
                    },
                )
        except Exception:
            continue

    return jobs


async def _crawl_glints(page: Page, query: str, location: str) -> list[dict]:
    """Crawl Glints search results."""
    city = location if location else ""
    url = SEARCH_URLS["glints"].format(query=query, city=city)
    success = await _navigate(page, url)
    if not success:
        return []

    jobs = []
    # Glints uses .opportunity-card or <li> within .opportunities-list
    cards = page.query_selector_all(
        ".opportunity-card, [class*='opportunity-card'], "
        ".opportunity-item, [class*='opportunity-item'], "
        ".job-list li, .result-item",
    )
    if not cards:
        # Fallback: try any anchor with /opportunities/jobs/
        links = page.query_selector_all('a[href*="/opportunities/jobs/"]')
        for a in links[:10]:
            href = a.get_attribute("href", timeout=3000) or ""
            text = _clean_text(a.inner_text(timeout=3000))
            if text and _is_job_url(href, "glints"):
                jobs.append(
                    {
                        "id": f"glints-se-{hashlib.md5((href + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "glints",
                        "title": text.split("\n")[0] if text else "Không rõ",
                        "company": "Không rõ công ty",
                        "location": None,
                        "salary": None,
                        "level": None,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else f"https://glints.com{href}",
                        "description_snippet": None,
                    },
                )
        return jobs

    for card in cards[:10]:
        try:
            title_el = card.query_selector(
                ".opportunity-name h3 a, h2 a, .title a, a[class*='title']",
            )
            company_el = card.query_selector(
                ".company-name, .company, .employer, [class*='company']",
            )
            location_el = card.query_selector(".location, .place, [class*='location']")
            salary_el = card.query_selector(".salary, .compensation, [class*='salary']")
            link_el = card.query_selector("a[href]")

            title = _clean_text(title_el.inner_text(timeout=3000)) if title_el else ""
            company = (
                _clean_text(company_el.inner_text(timeout=3000))
                if company_el
                else "Không rõ công ty"
            )
            company_logo_url = _extract_company_logo(card, "https://glints.com")
            location = (
                location_el.inner_text(timeout=3000).strip() if location_el else None
            )
            salary = salary_el.inner_text(timeout=3000).strip() if salary_el else None
            href = link_el.get_attribute("href", timeout=3000) if link_el else ""
            full_text = card.inner_text(timeout=3000).strip()

            if title:
                location = _infer_city(location or full_text)
                level = _infer_level(title)
                jobs.append(
                    {
                        "id": f"glints-se-{hashlib.md5((href or title + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "glints",
                        "title": title,
                        "company": company,
                        "company_logo_url": company_logo_url,
                        "location": location,
                        "salary": salary,
                        "level": level,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else (f"https://glints.com{href}" if href else ""),
                        "description_snippet": _clean_text(full_text[:300])
                        if full_text
                        else None,
                    },
                )
        except Exception:
            continue

    return jobs


async def _crawl_jobsgo(page: Page, query: str, location: str) -> list[dict]:
    """Crawl JobsGO search results."""
    city = location if location else ""
    url = SEARCH_URLS["jobsgo"].format(query=query, city=city)
    success = await _navigate(page, url)
    if not success:
        return []

    jobs = []
    cards = page.query_selector_all(
        ".job-item, .job-card, [class*='job-item'], [class*='job-card'], "
        "li.vacancy-item, .vacancy-list li",
    )
    if not cards:
        return []

    for card in cards[:10]:
        try:
            title_el = card.query_selector(
                "h3 a, h4 a, .job-title a, a[class*='title']",
            )
            company_el = card.query_selector(
                ".company-name, .company, [class*='company']",
            )
            location_el = card.query_selector(
                ".location, .address, [class*='location']",
            )
            salary_el = card.query_selector(".salary, [class*='salary']")
            link_el = card.query_selector("a[href]")

            title = _clean_text(title_el.inner_text(timeout=3000)) if title_el else ""
            company = (
                _clean_text(company_el.inner_text(timeout=3000))
                if company_el
                else "Không rõ công ty"
            )
            company_logo_url = _extract_company_logo(card, "https://jobsgo.vn")
            location = (
                location_el.inner_text(timeout=3000).strip() if location_el else None
            )
            salary = salary_el.inner_text(timeout=3000).strip() if salary_el else None
            href = link_el.get_attribute("href", timeout=3000) if link_el else ""
            full_text = card.inner_text(timeout=3000).strip()

            if title:
                location = _infer_city(location or full_text)
                level = _infer_level(title)
                jobs.append(
                    {
                        "id": f"jobsgo-se-{hashlib.md5((href or title + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "jobsgo",
                        "title": title,
                        "company": company,
                        "company_logo_url": company_logo_url,
                        "location": location,
                        "salary": salary,
                        "level": level,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else (f"https://jobsgo.vn{href}" if href else ""),
                        "description_snippet": _clean_text(full_text[:300])
                        if full_text
                        else None,
                    },
                )
        except Exception:
            continue

    return jobs


async def _crawl_vieclam24h(page: Page, query: str, location: str) -> list[dict]:
    """Crawl Vieclam24h search results."""
    city = location if location else ""
    url = SEARCH_URLS["vieclam24h"].format(query=query, city=city)
    success = await _navigate(page, url)
    if not success:
        return []

    jobs = []
    cards = page.query_selector_all(
        ".job-item, .job-card, [class*='job-item'], [class*='job-card'], "
        "li.result-item, .list-job li, .search-result-item",
    )
    if not cards:
        return []

    for card in cards[:10]:
        try:
            title_el = card.query_selector("h3 a, h4 a, .title a, a[class*='title']")
            company_el = card.query_selector(
                ".company-name, .company, [class*='company']",
            )
            location_el = card.query_selector(
                ".location, .address, [class*='location']",
            )
            salary_el = card.query_selector(".salary, [class*='salary']")
            link_el = card.query_selector("a[href]")

            title = _clean_text(title_el.inner_text(timeout=3000)) if title_el else ""
            company = (
                _clean_text(company_el.inner_text(timeout=3000))
                if company_el
                else "Không rõ công ty"
            )
            company_logo_url = _extract_company_logo(card, "https://www.vieclam24h.vn")
            location = (
                location_el.inner_text(timeout=3000).strip() if location_el else None
            )
            salary = salary_el.inner_text(timeout=3000).strip() if salary_el else None
            href = link_el.get_attribute("href", timeout=3000) if link_el else ""
            full_text = card.inner_text(timeout=3000).strip()

            if title:
                location = _infer_city(location or full_text)
                level = _infer_level(title)
                jobs.append(
                    {
                        "id": f"vieclam24h-se-{hashlib.md5((href or title + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "vieclam24h",
                        "title": title,
                        "company": company,
                        "company_logo_url": company_logo_url,
                        "location": location,
                        "salary": salary,
                        "level": level,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else (f"https://www.vieclam24h.vn{href}" if href else ""),
                        "description_snippet": _clean_text(full_text[:300])
                        if full_text
                        else None,
                    },
                )
        except Exception:
            continue

    return jobs


async def _crawl_vietnamworks(page: Page, query: str, location: str) -> list[dict]:
    """Crawl VietnamWorks search results."""
    url = SEARCH_URLS["vietnamworks"].format(query=query)
    success = await _navigate(page, url)
    if not success:
        return []

    jobs = []
    cards = page.query_selector_all(
        ".job-item, .job-card, [class*='job-item'], [class*='job-card'], "
        "li.result-item, .search-result li, .job-result",
    )
    if not cards:
        # Fallback: look for links matching VietnamWorks job pattern
        links = page.query_selector_all('a[href*="/viec-lam/"], a[href*="/job/"]')
        for a in links[:10]:
            href = a.get_attribute("href", timeout=3000) or ""
            text = _clean_text(a.inner_text(timeout=3000))
            if text and _is_job_url(href, "vietnamworks"):
                jobs.append(
                    {
                        "id": f"vietnamworks-se-{hashlib.md5((href + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "vietnamworks",
                        "title": text.split("\n")[0] if text else "Không rõ",
                        "company": "Không rõ công ty",
                        "location": None,
                        "salary": None,
                        "level": None,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else f"https://www.vietnamworks.com{href}",
                        "description_snippet": None,
                    },
                )
        return jobs

    for card in cards[:10]:
        try:
            title_el = card.query_selector("h3 a, h4 a, .title a, a[class*='title']")
            company_el = card.query_selector(
                ".company-name, .company, [class*='company']",
            )
            location_el = card.query_selector(
                ".location, .address, [class*='location']",
            )
            salary_el = card.query_selector(".salary, [class*='salary']")
            link_el = card.query_selector("a[href]")

            title = _clean_text(title_el.inner_text(timeout=3000)) if title_el else ""
            company = (
                _clean_text(company_el.inner_text(timeout=3000))
                if company_el
                else "Không rõ công ty"
            )
            company_logo_url = _extract_company_logo(
                card,
                "https://www.vietnamworks.com",
            )
            location = (
                location_el.inner_text(timeout=3000).strip() if location_el else None
            )
            salary = salary_el.inner_text(timeout=3000).strip() if salary_el else None
            href = link_el.get_attribute("href", timeout=3000) if link_el else ""
            full_text = card.inner_text(timeout=3000).strip()

            if title:
                location = _infer_city(location or full_text)
                level = _infer_level(title)
                jobs.append(
                    {
                        "id": f"vietnamworks-se-{hashlib.md5((href or title + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "vietnamworks",
                        "title": title,
                        "company": company,
                        "company_logo_url": company_logo_url,
                        "location": location,
                        "salary": salary,
                        "level": level,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": href
                        if href.startswith("http")
                        else (f"https://www.vietnamworks.com{href}" if href else ""),
                        "description_snippet": _clean_text(full_text[:300])
                        if full_text
                        else None,
                    },
                )
        except Exception:
            continue

    return jobs


# ===================================================================
# Direct HTTP crawlers (no Playwright needed)
# ===================================================================


async def _crawl_careerviet(query: str, location: str) -> list[dict]:
    """CareerViet — async Playwright scraping.

    CareerViet requires JS rendering. Uses Playwright to extract job links.
    URL pattern: /vi/tim-viec-lam/<id>.html
    """
    url = SEARCH_URLS["careerviet"].format(query=query)

    async with AsyncClient(timeout=Timeout(10.0), follow_redirects=True) as client:
        resp = await client.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return []

        html = resp.text
        jobs = []

        # CareerViet renders jobs as <a> links with href /vi/tim-viec-lam/<id>.html
        # Text is inside <div class="title"> wrapping the <a>
        link_pattern = re.compile(
            r'<a[^>]*href="(/vi/tim-viec-lam/[^\"]+\.html)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        for match in link_pattern.finditer(html):
            href, text = match.groups()
            text = re.sub(r"<[^>]+>", "", text).strip()
            if text:
                jobs.append(
                    {
                        "id": f"careerviet-{hashlib.md5((href + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "careerviet",
                        "title": _clean_text(text.split("\n")[0]),
                        "company": "Không rõ công ty",
                        "location": None,
                        "salary": None,
                        "level": None,
                        "skills": [],
                        "posted_text": "Hôm nay",
                        "url": f"https://careerviet.vn{href}",
                        "description_snippet": None,
                    },
                )

        return jobs[:10]


async def _crawl_ybox(query: str, location: str) -> list[dict]:
    """Ybox — direct HTTP scraping with embedded JSON extraction.

    Ybox renders job data in window.__INITIAL_ADS__ = {"Ads":{"count":"N","edges":[...]}}
    """
    url = SEARCH_URLS["ybox"].format(query=query)

    async with AsyncClient(timeout=Timeout(10.0), follow_redirects=True) as client:
        resp = await client.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return []

        html = resp.text
        jobs = []

        # Extract JSON from __INITIAL_ADS__ using brace-matching
        # Structure: __INITIAL_ADS__ = {"Ads":{"count":"N","edges":[{post:{...}}]}}
        start = html.find("__INITIAL_ADS__")
        if start < 0:
            return []
        start = html.find("{", start)
        if start < 0:
            return []

        # Brace-matching to extract the full JSON object
        depth = 0
        end = start
        for i in range(start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end <= start:
            return []

        json_str = html[start:end]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return []

        # Navigate to edges: data -> Ads -> edges -> edges
        try:
            edges = data.get("Ads", {}).get("edges", [])
            if isinstance(edges, dict):
                edges = edges.get("edges", [])
        except Exception:
            return []

        for edge in edges[:10]:
            try:
                post = edge.get("post", edge) if isinstance(edge, dict) else {}
                title = post.get("title", "")
                if not title:
                    continue

                publisher = post.get("publisher", {})
                company = publisher.get(
                    "fullName",
                    publisher.get("username", "Không rõ công ty"),
                )
                raw_logo = (
                    publisher.get("logo")
                    or publisher.get("avatar")
                    or publisher.get("image")
                    or publisher.get("avatarUrl")
                )
                if isinstance(raw_logo, dict):
                    raw_logo = raw_logo.get("url") or raw_logo.get("src")
                company_logo_url = _safe_company_logo_url(raw_logo, "https://ybox.vn")

                slug = post.get("slug", "")
                post_id = post.get("_id", post.get("id", ""))
                job_url = f"https://ybox.vn/tuyen-dung/{slug}-{post_id}" if slug else ""

                summary = post.get("summary", "")

                # Infer location from title/description
                full_text = f"{title} {summary}"
                job_location = _infer_city(full_text)
                level = _infer_level(title)
                salary = _infer_salary(full_text)

                jobs.append(
                    {
                        "id": f"ybox-{post_id}-{hashlib.md5((job_url + str(len(jobs))).encode()).hexdigest()[:8]}",
                        "source": "ybox",
                        "title": _clean_text(title),
                        "company": company,
                        "company_logo_url": company_logo_url,
                        "location": job_location,
                        "salary": salary,
                        "level": level,
                        "skills": _extract_skills(full_text),
                        "posted_text": "Hôm nay",
                        "url": job_url,
                        "description_snippet": _clean_text(summary[:300])
                        if summary
                        else None,
                    },
                )
            except Exception:
                continue

        return jobs


# ===================================================================
# Source dispatcher
# ===================================================================

_ASYNC_CRAWLERS = {
    "itviec": _crawl_itviec,
    "topcv": _crawl_topcv,
    "glints": _crawl_glints,
    "jobsgo": _crawl_jobsgo,
    "vieclam24h": _crawl_vieclam24h,
    "vietnamworks": _crawl_vietnamworks,
}

_HTTP_CRAWLERS = {
    "careerviet": _crawl_careerviet,
    "ybox": _crawl_ybox,
}


async def crawl_source(
    source: str,
    query: str,
    location: str,
    page: Page | None,
) -> tuple[list[dict], str | None]:
    """Run a single source crawler. Returns (jobs, error)."""
    try:
        if source in _ASYNC_CRAWLERS:
            if page is None:
                return [], "browser unavailable"
            fn = _ASYNC_CRAWLERS[source]
            jobs = await asyncio.wait_for(fn(page, query, location), timeout=20)
            return jobs, None
        if source in _HTTP_CRAWLERS:
            fn = _HTTP_CRAWLERS[source]
            jobs = await asyncio.wait_for(fn(query, location), timeout=15)
            return jobs, None
        return [], f"Unknown source: {source}"
    except asyncio.TimeoutError:
        return [], "timeout"
    except Exception as e:
        return [], str(e)


# ===================================================================
# Query generation
# ===================================================================


def generate_search_queries(
    target_roles: list[str],
    skills: list[str],
    location: str,
    override_role: str | None = None,
) -> list[str]:
    """Generate search queries from candidate profile.

    Returns 2-4 queries for use across all job boards.
    """
    roles = [override_role] if override_role else target_roles[:2]
    if not roles:
        roles = ["Developer"]

    queries: list[str] = []

    for role in roles:
        # Get role-compatible skills (first 2)
        role_skills = skills[:2]

        # Query 1: Role + top skill + location
        top_skill = role_skills[0] if role_skills else ""
        q1 = f"{role} {top_skill} {location}".strip().replace("  ", " ")
        if q1:
            queries.append(q1)

        # Query 2: Role + location
        q2 = f"{role} {location}".strip()
        if q2:
            queries.append(q2)

        # Query 3: Skill + role (if extra skill)
        if len(role_skills) > 1:
            q3 = f"{role_skills[1]} {role}".strip()
            if q3:
                queries.append(q3)

        # Query 4: Role alone
        queries.append(role)

    # Deduplicate, filter short/empty
    seen: set[str] = set()
    result: list[str] = []
    for q in queries:
        # Remove non-alphanumeric/extras (keep unicode letters via unicodedata)
        clean = re.sub(r"[^a-zA-Z0-9\s+-]", "", q).lower().strip().replace("  ", " ")
        if clean and len(clean) > 2 and clean not in seen:
            seen.add(clean)
            result.append(clean)
            if len(result) >= 4:
                break

    return result


# ===================================================================
# Deduplication
# ===================================================================


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate jobs by URL, then title+company, then title+location."""
    seen_urls: set[str] = set()
    seen_tc: set[str] = set()
    seen_tl: set[str] = set()
    unique: list[dict] = []

    for job in jobs:
        clean_url = job.get("url", "").split("?")[0].strip().lower()
        norm_title = _normalize_key(job.get("title", ""))
        norm_company = _normalize_key(job.get("company", "") or "")
        norm_location = _normalize_key(job.get("location", "") or "")

        tc_key = f"{norm_title}_{norm_company}"
        tl_key = f"{norm_title}_{norm_location}"

        if clean_url in seen_urls:
            continue
        if norm_title and norm_company and tc_key in seen_tc:
            continue
        if norm_title and norm_location and tl_key in seen_tl:
            company = job.get("company", "") or ""
            if not company or "Employer" in company:
                continue

        seen_urls.add(clean_url)
        if norm_title and norm_company:
            seen_tc.add(tc_key)
        if norm_title and norm_location:
            seen_tl.add(tl_key)

        unique.append(job)

    return unique


def _normalize_key(s: str) -> str:
    """Normalize string for dedup comparison."""
    import unicodedata

    normalized = unicodedata.normalize("NFD", s.lower())
    # Remove combining diacritical marks (Vietnamese accents)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    normalized = normalized.replace("đ", "d")
    return re.sub(r"[^a-z0-9]", "", normalized).strip()


# ===================================================================
# Ranking
# ===================================================================

_LEVEL_HIERARCHY: dict[str, int] = {
    "intern": 0,
    "fresher": 1,
    "junior": 2,
    "middle": 3,
    "senior": 4,
    "unknown": 2,
}

_MIN_GOOD_MATCH_SCORE = 70
_MIN_STRETCH_SCORE = 50
_MAX_STRETCH_RESULTS = 3


def _is_closed_job(job: dict) -> bool:
    """Return True when a source explicitly marks a listing as unavailable."""
    status = _normalize_key(str(job.get("status") or ""))
    if status in {
        "closed",
        "expired",
        "inactive",
        "filled",
        "dadong",
        "hethan",
        "ngungtuyen",
    }:
        return True

    availability_text = " ".join(
        str(job.get(field) or "")
        for field in ("posted_text", "title", "description_snippet")
    ).lower()
    normalized_text = _normalize_key(availability_text)
    closed_markers = (
        "dadong",
        "daketthuc",
        "hethanungtuyen",
        "hetnhanhoso",
        "ngungtuyen",
        "jobclosed",
        "jobexpired",
        "positionfilled",
        "applicationsclosed",
        "nolongeracceptingapplications",
    )
    return any(marker in normalized_text for marker in closed_markers)


def rank_jobs(
    jobs: list[dict],
    target_roles: list[str],
    skills: list[str],
    seniority: str,
    location: str,
    show_stretch: bool = True,
) -> list[dict]:
    """Rank jobs by match score against candidate profile."""
    ranked = [
        calculate_match(job, target_roles, skills, seniority, location)
        for job in jobs
        if not _is_closed_job(job)
    ]

    # Sort by score descending
    ranked.sort(key=lambda j: j["match_score"], reverse=True)

    good_matches = [
        job for job in ranked if job["match_score"] >= _MIN_GOOD_MATCH_SCORE
    ]
    if not show_stretch:
        return good_matches

    stretch_matches = [
        job
        for job in ranked
        if _MIN_STRETCH_SCORE <= job["match_score"] < _MIN_GOOD_MATCH_SCORE
    ][:_MAX_STRETCH_RESULTS]
    return good_matches + stretch_matches


def calculate_match(
    job: dict,
    target_roles: list[str],
    skills: list[str],
    seniority: str,
    location: str,
) -> dict:
    """Calculate match score for a single job."""
    title_score = 0
    skill_score = 0
    seniority_score = 0
    location_score = 0
    recency_score = 0
    seniority_penalty = 0

    match_reasons: list[str] = []
    missing_skills: list[str] = []

    job_title = (job.get("title") or "").lower()
    job_desc = ((job.get("description_snippet") or "") + " " + job_title).lower()

    # 1. Title match (35%)
    roles = target_roles if target_roles else ["Developer"]
    best_title = 0
    for role in roles:
        role_lower = role.lower()
        if role_lower in job_title:
            best_title = 35
            break
        # Fuzzy word match
        role_tokens = role_lower.replace("/", " ").replace("-", " ").split()
        job_tokens = job_title.replace("/", " ").replace("-", " ").split()
        matched = sum(1 for w in role_tokens if w in job_tokens)
        score = round((matched / max(len(role_tokens), 1)) * 25)
        best_title = max(best_title, score)

    title_score = best_title
    if title_score >= 25:
        match_reasons.append(
            "Tiêu đề công việc trùng khớp với định hướng vai trò của bạn.",
        )

    # 2. Skill overlap (35%)
    job_skills = [s.lower() for s in job.get("skills", [])]
    cand_skills = _normalize_skill_list(skills)

    if job_skills:
        overlap = sum(
            1 for js in job_skills if any(_skills_overlap(js, cs) for cs in cand_skills)
        )
        base = max(1, min(len(job_skills), len(cand_skills)))
        skill_score = round((overlap / base) * 35)

        # Track missing
        for js in job_skills:
            if not any(_skills_overlap(js, cs) for cs in cand_skills):
                missing_skills.append(js.title())
    else:
        # Scan description for skill mentions
        match_count = sum(
            1
            for cs in cand_skills
            if re.search(r"\b" + re.escape(cs) + r"\b", job_desc, re.IGNORECASE)
        )
        if match_count >= 3:
            skill_score = 35
        elif match_count == 2:
            skill_score = 25
        elif match_count == 1:
            skill_score = 15

    if skill_score >= 25:
        match_reasons.append("Bộ kỹ năng của bạn đáp ứng tốt yêu cầu công nghệ.")

    # 3. Seniority (15%)
    cand_level = seniority or "unknown"
    job_level = job.get("level") or "unknown"

    cand_rank = _LEVEL_HIERARCHY.get(cand_level, 2)
    job_rank = _LEVEL_HIERARCHY.get(job_level, 2)

    if cand_level == "unknown" or job_level == "unknown":
        seniority_score = 10
    elif cand_rank == job_rank:
        seniority_score = 15
        match_reasons.append(
            "Cấp bậc công việc phù hợp với cấp độ kinh nghiệm của bạn.",
        )
    elif job_rank > cand_rank:
        diff = job_rank - cand_rank
        if diff >= 2:
            seniority_score = 0
            seniority_penalty = 30
            match_reasons.append(
                "Yêu cầu kinh nghiệm cao hơn đáng kể so với hồ sơ của bạn.",
            )
        else:
            seniority_score = 8
            seniority_penalty = 10
            match_reasons.append(
                "Yêu cầu kinh nghiệm hơi cao hơn so với hồ sơ của bạn (Stretch).",
            )
    else:
        seniority_score = 10
        match_reasons.append(
            "Bạn có thể có năng lực cao hơn so với cấp bậc yêu cầu của công việc.",
        )

    # 4. Location (10%)
    cand_loc = (location or "").lower()
    job_loc = (
        (job.get("location") or "") + " " + (job.get("description_snippet") or "")
    ).lower()

    if not cand_loc:
        location_score = 10
    elif cand_loc in job_loc or job_loc in cand_loc:
        location_score = 10
        match_reasons.append(
            f"Địa điểm làm việc thuận tiện ({job.get('location', '')}).",
        )
    elif "remote" in job_loc or "toàn quốc" in job_loc or "online" in job_loc:
        location_score = 8
        match_reasons.append("Công việc hỗ trợ làm việc từ xa (Remote/Online).")
    # else 0

    # 5. Recency (5%)
    posted = ((job.get("posted_text") or "") + "").lower()
    if any(kw in posted for kw in ["giờ", "hôm nay", "1 ngày"]):
        recency_score = 5
    elif any(kw in posted for kw in ["2 ngày", "3 ngày"]):
        recency_score = 4
    elif any(kw in posted for kw in ["4 ngày", "7 ngày", "tuần"]):
        recency_score = 3
    else:
        recency_score = 2

    final = max(
        0,
        min(
            100,
            title_score
            + skill_score
            + seniority_score
            + location_score
            + recency_score
            - seniority_penalty,
        ),
    )
    label = "good_match" if final >= _MIN_GOOD_MATCH_SCORE else "stretch"

    result = dict(job)
    result["match_score"] = final
    result["match_label"] = label
    result["match_reasons"] = match_reasons[:3]
    result["missing_skills"] = missing_skills
    return result


def _normalize_skill_list(skills: list[str]) -> list[str]:
    """Normalize skill names for comparison."""
    normalized = []
    for s in skills:
        s = s.lower()
        s = (
            s.replace("reactjs", "react")
            .replace("nextjs", "next.js")
            .replace("nodejs", "node.js")
            .strip()
        )
        normalized.append(s)
    return normalized


def _skills_overlap(cand: str, job: str) -> bool:
    """Check if two skill strings represent the same skill."""
    if cand == job:
        return True
    if cand in job or job in cand:
        return True
    # Special cases
    pairs = [
        ("machine learning", "deep learning"),
        ("machine learning", "ai"),
        ("deep learning", "ai"),
    ]
    return any({cand, job} == {a, b} for a, b in pairs)


# ===================================================================
# Orchestrator — main entry point
# ===================================================================


async def search_jobs(
    cv_text: str,
    target_roles: list[str],
    skills: list[str],
    seniority: str,
    location: str,
    years_of_experience: float,
    queries: list[str],
    enabled_sources: list[str] | None = None,
    limit_per_source: int = 8,
    show_stretch: bool = True,
    target_role_override: str | None = None,
) -> dict:
    """Main job search orchestrator.

    1. Generates search queries from profile
    2. Crawls each source concurrently
    3. Deduplicates and ranks results
    4. Returns structured response
    """
    if enabled_sources is None:
        enabled_sources = [
            "itviec",
            "topcv",
            "vietnamworks",
            "ybox",
            "glints",
            "jobsgo",
            "careerviet",
            "vieclam24h",
        ]

    # Generate queries from profile
    gen_queries = generate_search_queries(
        target_roles,
        skills,
        location,
        target_role_override,
    )
    final_queries = queries if queries else gen_queries[:4]

    source_status: list[dict] = []
    all_jobs: list[dict] = []

    async def run_source(
        src: str,
        page: Page | None,
        browser_error: str | None = None,
    ) -> None:
        """Run crawler first (free, no API credit), search engine as fallback.

        The Playwright crawler is the primary data source because it doesn't
        consume API credits. The search engine (Serper/Google CSE) is used
        as a fallback only when the crawler returns 0 results — for example
        when sites block bots with Cloudflare or JS-heavy rendering breaks
        selectors.
        """
        from app.services.search_engine import search_via_engine_for_source

        primary_query = final_queries[0] if final_queries else "Developer"
        error: str | None = browser_error

        # Map source to search engine domain
        domain_map = {
            "itviec": "itviec.com",
            "topcv": "topcv.vn",
            "glints": "glints.com",
            "jobsgo": "jobsgo.vn",
            "vieclam24h": "vieclam24h.vn",
            "vietnamworks": "vietnamworks.com",
            "ybox": "ybox.vn",
            "careerviet": "careerviet.vn",
        }
        domain = domain_map.get(src, src)

        is_crawlable = src in _ASYNC_CRAWLERS or src in _HTTP_CRAWLERS

        # Phase 1: Crawler (primary, free — no API credit cost)
        jobs: list[dict] = []
        status = "empty"

        if src in _ASYNC_CRAWLERS and page is None:
            status = "failed"
        elif is_crawlable:
            jobs, error = await crawl_source(src, primary_query, location, page)
            if error == "timeout":
                status = "timeout"
            elif error:
                status = "failed"
            else:
                status = "success" if jobs else "empty"

            # Try secondary query for crawler
            if not jobs and len(final_queries) > 1:
                secondary_query = final_queries[1]
                jobs2, _ = await crawl_source(src, secondary_query, location, page)
                existing_urls = {j.get("url", "") for j in jobs}
                for j in jobs2:
                    if j.get("url") not in existing_urls:
                        jobs.append(j)
                        existing_urls.add(j.get("url", ""))
                if jobs:
                    status = "success"

        # Phase 2: Search engine fallback — only when crawler returned 0 results
        se_jobs: list[dict] = []
        if not jobs and status != "timeout":
            try:
                se_jobs = await search_via_engine_for_source(
                    src,
                    primary_query,
                    domain,
                    limit=limit_per_source,
                )
            except Exception as exc:
                se_jobs = []
                error = error or str(exc)
            if se_jobs:
                jobs = se_jobs
                status = "success"

            # Try secondary query for search engine
            if not jobs and len(final_queries) > 1:
                secondary_query = final_queries[1]
                try:
                    se_jobs2 = await search_via_engine_for_source(
                        src,
                        secondary_query,
                        domain,
                        limit=limit_per_source,
                    )
                except Exception as exc:
                    se_jobs2 = []
                    error = error or str(exc)
                if se_jobs2:
                    jobs = se_jobs2
                    status = "success"

        source_status.append(
            {
                "source": src,
                "status": status,
                "count": len(jobs),
                "error": None if status in ("success", "empty") else error,
            },
        )
        all_jobs.extend(jobs)

    # Run sources with concurrency limit of 2. Browser startup is best-effort:
    # Render can temporarily be unable to launch Chromium, while the HTTP and
    # configured search-engine fallbacks remain usable.
    semaphore = asyncio.Semaphore(2)

    async def run_enabled_sources(
        page: Page | None,
        browser_error: str | None = None,
    ) -> None:
        async def limited_run(src: str) -> None:
            async with semaphore:
                await run_source(src, page, browser_error)

        tasks = [
            asyncio.create_task(limited_run(src))
            for src in enabled_sources
            if src in _ASYNC_CRAWLERS or src in _HTTP_CRAWLERS
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    try:
        async with managed_browser() as browser_mgr:
            page = await browser_mgr.new_page()
            await run_enabled_sources(page)
    except Exception as exc:
        await run_enabled_sources(None, f"browser unavailable: {exc}")

    # Deduplicate
    unique_jobs = deduplicate_jobs(all_jobs)

    # Rank
    ranked = rank_jobs(
        unique_jobs,
        target_roles,
        skills,
        seniority,
        location,
        show_stretch,
    )

    return {
        "profile": {
            "targetRoles": target_roles,
            "skills": skills,
            "seniority": seniority,
            "location": location,
            "yearsOfExperience": years_of_experience,
        },
        "total": len(ranked),
        "jobs": ranked,
        "sourceStatus": source_status,
        "queries": final_queries,
    }
