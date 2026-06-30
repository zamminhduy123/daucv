# Job Search Crawler — Implementation Status

## What's Done

### Backend (Playwright + Serper)
- `app/services/job_crawler.py` — Full Playwright service:
  - Browser manager (singleton, stealth headers, webdriver hiding)
  - 6 async Playwright crawlers: ITviec, TopCV, Glints, JobsGO, Vieclam24h, VietnamWorks
  - 2 direct HTTP crawlers: CareerViet (httpx + regex), Ybox (embedded JSON extraction)
  - Query generation from candidate profile
  - Deduplication (URL, title+company, title+location)
  - Ranking (title 35%, skills 35%, seniority 15%, location 10%, recency 5%)
  - Orchestrator: concurrent source crawling (limit 2), search engine fallback
- `app/services/search_engine.py` — Serper API / Google CSE adapter:
  - Queries `site:domain` constraints for each job board
  - Parses title/company/salary/location/skills from search snippets
  - URL validation per domain
  - **Fallback data source** (used when crawler returns 0 results — requires Serper API key)
- `app/api/routes/jobs.py` — FastAPI route at `POST /api/jobs/search`:
  - LLM-based CV profile parsing with rule-based fallback
  - Manual role/location override support
  - Returns `{ profile, total, jobs, sourceStatus, queries }`
- `app/models/requests.py` — `JobSearchRequest` model
- `app/models/responses.py` — `JobResult`, `RankedJobResult`, `JobSourceStatus` models
- `app/main.py` — Jobs router registered
- `requirements.txt` — playwright added

### Frontend
- `src/app/api/jobs/search/route.ts` — Next.js API route proxied to backend
- Frontend job-sources (`lib/jobs/`) fully removed — all search/rank/dedupe logic
  now handled by the backend API

### Infrastructure
- Chromium browser installed (playwright v1228)
- `backend/.env` — SERPER_API_KEY placeholder added

## What Still Needs Work

### High Priority
1. **Get Serper API key** — Sign up at https://serper.dev (free: 2500 req/mo), paste into `backend/.env`
   - **Important**: Mock results have been removed — without a key, search engine fallback returns 0 results
   - With key: live Google results kick in when Playwright crawler fails (Cloudflare, stale selectors)
   - Crawler (Playwright) is the primary source (free, no API credit cost); search engine is the fallback

2. **CareerViet/Ybox selector refinement** — company extraction returns "Không rõ công ty":
   - CareerViet: need to find company name in surrounding DOM (currently only extracts `<a>` text)
   - Ybox: company extraction works in test but may need review on live page
   - Salary/location extraction from CareerViet also needs work

3. **Playwright crawler selector tuning** — live site HTML may differ from test snapshot:
   - ITviec: selectors `div.it-job-card`, `h2 a`, etc. — need verification against live DOM
   - TopCV: selectors `div.job-item`, `h3 a` — need verification
   - Glints: selectors `.opportunity-card`, `.opportunity-name` — need verification
   - JobsGO: selectors `.job-item` — live page returned `{"success":1}` JSON, may be API-driven
   - Vieclam24h: selectors may need updating
   - VietnamWorks: selectors may need updating

### Medium Priority
4. ~~**Remove frontend self-contained crawl logic**~~ ✅ **DONE** — deleted `frontend/src/lib/jobs/` entirely (job-sources, dedupe, query, rank, types, cache). All job search/ranking now handled by backend API.

5. **Error handling improvements**:
   - Browser launch failures → graceful degradation
   - Per-source timeout handling with specific error messages
   - Rate limiting / retry logic for Serper API
   - 120s request timeout may need tuning (Playwright + LLM can take longer)

6. **Skill extraction from Playwright crawlers** — currently returns `[]` for Playwright sources because:
   - Playwright crawlers don't call `_extract_skills()` on extracted text
   - Need to add skill extraction to each crawler's result mapping

7. **Posted date extraction** — all sources return "Hôm nay" (hardcoded):
   - Need to extract actual posted dates from DOM
   - Affects recency scoring in ranking

### Low Priority
8. **Test the full frontend flow**:
   - Start Next.js dev server
   - Upload CV, go to jobs page, verify crawl results display correctly
   - Check that source status indicators show correct icons/colors
   - Verify job cards render with match scores, filters work

9. **Performance optimization**:
   - Playwright browser pool reuse (currently singleton, may need connection reuse across requests)
   - Caching results (same CV → same results)
   - Background task execution for long searches

10. **Unit tests** for:
    - Query generation
    - Deduplication logic
    - Ranking/scoring
    - Skill extraction
    - URL validation
