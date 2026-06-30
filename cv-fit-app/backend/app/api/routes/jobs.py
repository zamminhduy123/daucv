"""
Job Finder routes — search Vietnamese job boards.

POST /api/jobs/search
    Accepts a CV text payload, extracts candidate profile (via LLM + rule-based
    fallback), crawls all configured job boards with Playwright, deduplicates,
    ranks, and returns matching jobs with match scores.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks

from app.models.requests import JobSearchRequest
from app.models.responses import CandidateProfileResponse, JobSourceStatus, JobResult, RankedJobResult
from app.prompts.system_prompts import build_job_parser_prompt
from app.services.ai_service import call_llm_with_fallback
from app.services.job_crawler import search_jobs, generate_search_queries
from app.models.domain import Message

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _rule_based_parse(cv_text: str) -> CandidateProfileResponse:
    """Rule-based CV parser fallback (ported from frontend parseCV.ts).

    This mirrors the frontend parseCV logic so we have a fallback when the
    LLM endpoint is unavailable.
    """
    normalized = cv_text.lower()

    # Skills dictionary
    SKILLS = [
        "javascript", "typescript", "html", "css", "sass", "less", "tailwind", "bootstrap",
        "react", "reactjs", "react native", "vue", "vuejs", "angular", "next.js", "nextjs",
        "nodejs", "express", "expressjs", "nestjs", "fastapi", "django", "flask", "laravel",
        "spring boot", "spring", "asp.net", ".net core", "c#", "java", "python", "golang", "go",
        "php", "ruby", "rails", "swift", "kotlin", "flutter", "dart", "rust", "c++", "c",
        "sql", "mysql", "postgresql", "postgres", "mongodb", "nosql", "redis", "firebase",
        "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "jenkins", "git", "github", "gitlab",
        "ci/cd", "figma", "ui/ux", "scrum", "agile", "testing", "qa", "qc", "jest", "cypress",
        "selenium", "machine learning", "deep learning", "ai", "nlp", "data analysis"
    ]

    ROLES = {
        "Frontend Developer": ["frontend", "front-end", "front end", "react developer", "web developer", "ui developer"],
        "Backend Developer": ["backend", "back-end", "back end", "nodejs developer", "java developer", "python developer", "php developer"],
        "Fullstack Developer": ["fullstack", "full-stack", "full stack", "fullstack developer"],
        "Mobile Developer": ["mobile", "android", "ios", "react native", "flutter", "swift", "kotlin"],
        "DevOps Engineer": ["devops", "sre", "system admin", "cloud engineer"],
        "Data Engineer": ["data engineer", "data engineering", "etl", "big data"],
        "AI Engineer": ["ai engineer", "ai developer", "ai research", "nlp", "ai/ml", "generative ai"],
        "Machine Learning Engineer": ["ml engineer", "machine learning engineer", "deep learning engineer", "machine learning", "deep learning"],
        "Data Scientist": ["data scientist", "data science", "statistician"],
        "QA/QC Tester": ["tester", "qa", "qc", "quality assurance", "test engineer"],
        "Business Analyst": ["business analyst", "ba", "product owner"],
        "Project Manager": ["project manager", "pm", "scrum master"],
    }

    SENIORITY_KW = {
        "intern": ["intern", "thực tập", "thực tập sinh", "internship"],
        "fresher": ["fresher", "mới tốt nghiệp", "entry level", "no experience"],
        "junior": ["junior", "dưới 2 năm", "1 năm kinh nghiệm", "1 year experience"],
        "middle": ["middle", "mid-level", "2 năm kinh nghiệm", "3 năm kinh nghiệm", "2 years experience", "3 years experience"],
        "senior": ["senior", "trưởng nhóm", "lead", "4 năm kinh nghiệm", "5 năm kinh nghiệm", "4 years experience", "5 years experience"],
    }

    # Extract skills
    import re
    skills = []
    for skill in SKILLS:
        escaped = skill.replace("-", r"\-").replace("+", r"\+").replace(".", r"\.").replace("*", r"\*")
        if skill in ("c", "go"):
            pattern = r'\b' + escaped + r'\b'
        elif skill in ("c++", ".net core", "c#", "asp.net", "next.js"):
            pattern = r'(?:\b|\s|^)' + escaped + r'(?:\b|\s|$|,)'
        else:
            pattern = r'\b' + escaped + r'\b'
        if re.search(pattern, normalized, re.I):
            formatted = " ".join(w.capitalize() for w in skill.split(" "))
            skills.append(formatted)

    # Infer roles
    role_scores = {}
    for role, keywords in ROLES.items():
        score = 0
        for kw in keywords:
            escaped = kw.replace("-", r"\-")
            pattern = r'\b' + escaped + r'\b'
            matches = re.findall(pattern, normalized, re.I)
            score += len(matches)
        if score > 0:
            role_scores[role] = score

    target_roles = sorted(role_scores.keys(), key=lambda r: role_scores[r], reverse=True)
    if not target_roles:
        target_roles = ["Software Engineer"]

    # Seniority
    seniority = "unknown"
    years_of_experience = 0

    # Extract years of experience
    eng_exp = re.search(r'(\d+)\s*(?:year|yr)s?\s*(?:of\s*)?experience', normalized, re.I)
    vi_exp = re.search(r'(\d+)\s*năm\s*kinh\s*nghiệm', normalized, re.I)
    matched = eng_exp or vi_exp
    if matched:
        years_of_experience = int(matched.group(1))
        if years_of_experience >= 5:
            seniority = "senior"
        elif years_of_experience >= 3:
            seniority = "middle"
        elif years_of_experience >= 1:
            seniority = "junior"
        else:
            seniority = "fresher"

    if seniority == "unknown":
        max_score = -1
        for level, keywords in SENIORITY_KW.items():
            score = 0
            for kw in keywords:
                escaped = kw.replace("-", r"\-")
                pattern = r'\b' + escaped + r'\b'
                if re.findall(pattern, normalized, re.I):
                    score += 1
            if score > max_score and score > 0:
                max_score = score
                seniority = level

    # Location
    location = None
    cities = {
        "hồ chí minh": "Hồ Chí Minh", "ho chi minh": "Hồ Chí Minh",
        "hcm": "Hồ Chí Minh", "sài gòn": "Hồ Chí Minh", "saigon": "Hồ Chí Minh",
        "hà nội": "Hà Nội", "ha noi": "Hà Nội", "hn": "Hà Nội",
        "đà nẵng": "Đà Nẵng", "da nang": "Đà Nẵng",
    }
    for key, city in cities.items():
        if key in normalized:
            location = city
            break

    return CandidateProfileResponse(
        target_roles=target_roles,
        skills=skills,
        seniority=seniority,
        location=location or "",
        years_of_experience=float(years_of_experience),
        queries=[],
    )


@router.post("/search", response_model=dict)
async def search_jobs_endpoint(
    req: JobSearchRequest,
    background_tasks: BackgroundTasks,
):
    """Search Vietnamese job boards for positions matching the candidate's CV.

    Flow:
    1. Parse candidate profile from CV (LLM → rule-based fallback)
    2. Generate search queries
    3. Crawl configured job boards concurrently with Playwright
    4. Deduplicate, rank, and return results
    """
    # Step 1: Parse profile
    try:
        prompt = build_job_parser_prompt(req.cv_text)
        response_text = await call_llm_with_fallback([Message(role="user", content=prompt)])

        # Parse JSON from LLM response
        import json
        # Try to extract JSON from the response
        import re as _re
        json_match = _re.search(r'\{[^{}]*"target_roles"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            raw = json.loads(json_match.group(0))
        else:
            raw = json.loads(response_text)

        profile = CandidateProfileResponse(
            target_roles=raw.get("target_roles", []),
            skills=raw.get("skills", []),
            seniority=raw.get("seniority", "unknown"),
            location=raw.get("location", ""),
            years_of_experience=raw.get("years_of_experience", 0),
            queries=raw.get("queries", []),
        )
    except Exception as e:
        # Fall back to rule-based parsing
        profile = _rule_based_parse(req.cv_text)

    # Apply manual overrides
    if req.target_role:
        profile.target_roles = [req.target_role] + [
            r for r in profile.target_roles if r != req.target_role
        ]
    if req.location:
        profile.location = req.location

    # Step 2: Generate search queries
    queries = profile.queries
    if not queries:
        queries = generate_search_queries(
            profile.target_roles,
            profile.skills,
            profile.location,
            req.target_role,
        )

    # Step 3: Crawl sources
    enabled_sources = req.sources or [
        "itviec", "topcv", "vietnamworks", "ybox",
        "glints", "jobsgo", "careerviet", "vieclam24h",
    ]

    result = await search_jobs(
        cv_text=req.cv_text,
        target_roles=profile.target_roles,
        skills=profile.skills,
        seniority=profile.seniority,
        location=profile.location,
        years_of_experience=profile.years_of_experience,
        queries=queries,
        enabled_sources=enabled_sources,
        limit_per_source=8,
        show_stretch=True,
        target_role_override=req.target_role,
    )

    # Step 4: Format response
    return {
        "profile": {
            "targetRoles": result["profile"]["targetRoles"],
            "skills": result["profile"]["skills"],
            "seniority": result["profile"]["seniority"],
            "location": result["profile"]["location"],
            "yearsOfExperience": result["profile"]["yearsOfExperience"],
        },
        "total": result["total"],
        "jobs": [
            {
                "id": job["id"],
                "source": job["source"],
                "title": job["title"],
                "company": job.get("company"),
                "location": job.get("location"),
                "salary": job.get("salary"),
                "level": job.get("level"),
                "skills": job.get("skills", []),
                "postedText": job.get("posted_text"),
                "url": job["url"],
                "descriptionSnippet": job.get("description_snippet"),
                "matchScore": job["match_score"],
                "matchLabel": job["match_label"],
                "matchReasons": job.get("match_reasons", []),
                "missingSkills": job.get("missing_skills", []),
            }
            for job in result["jobs"]
        ],
        "sourceStatus": result["sourceStatus"],
        "queries": result["queries"],
    }
