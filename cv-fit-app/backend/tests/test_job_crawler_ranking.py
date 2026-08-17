"""Regression tests for JOB SCAN result quality."""

from app.services.job_crawler import (
    _extract_company_logo,
    _safe_company_logo_url,
    rank_jobs,
)


def _job(job_id: str, *, posted_text: str = "Hôm nay") -> dict:
    return {
        "id": job_id,
        "source": "topcv",
        "title": "Frontend Developer",
        "company": "Acme",
        "company_logo_url": "https://cdn.example.com/acme.png",
        "location": "Hà Nội",
        "salary": None,
        "level": "junior",
        "skills": ["React", "TypeScript"],
        "posted_text": posted_text,
        "url": f"https://example.com/jobs/{job_id}",
        "description_snippet": "Build web applications with React and TypeScript.",
    }


def test_rank_jobs_removes_closed_listings_and_limits_stretch_results() -> None:
    good_match = _job("good")
    closed_match = _job("closed", posted_text="Đã đóng")

    stretch_jobs = []
    for index in range(6):
        job = _job(f"stretch-{index}")
        job["title"] = "Frontend Engineer"
        job["skills"] = ["React", "Go", "Kubernetes"]
        stretch_jobs.append(job)

    ranked = rank_jobs(
        [good_match, closed_match, *stretch_jobs],
        target_roles=["Frontend Developer"],
        skills=["React", "TypeScript"],
        seniority="junior",
        location="Hà Nội",
        show_stretch=True,
    )

    assert [job["id"] for job in ranked if job["match_label"] == "good_match"] == [
        "good",
    ]
    assert len([job for job in ranked if job["match_label"] == "stretch"]) == 3
    assert all(job["match_score"] >= 50 for job in ranked)


def test_company_logo_urls_are_normalized_and_reject_unsafe_schemes() -> None:
    assert (
        _safe_company_logo_url("/media/acme.png", "https://topcv.vn")
        == "https://topcv.vn/media/acme.png"
    )
    assert (
        _safe_company_logo_url(
            "https://cdn.topcv.vn/media/acme.png",
            "https://topcv.vn",
        )
        == "https://cdn.topcv.vn/media/acme.png"
    )
    assert (
        _safe_company_logo_url("https://example.com/acme.png", "https://topcv.vn")
        is None
    )
    assert (
        _safe_company_logo_url("http://topcv.vn/acme.png", "https://topcv.vn") is None
    )
    assert (
        _safe_company_logo_url("https://127.0.0.1/acme.png", "https://topcv.vn") is None
    )
    assert (
        _safe_company_logo_url("data:image/png;base64,abc", "https://topcv.vn") is None
    )
    assert _safe_company_logo_url("javascript:alert(1)", "https://topcv.vn") is None


def test_company_logo_extraction_uses_lazy_loaded_card_image() -> None:
    class FakeImage:
        def get_attribute(self, attribute: str, timeout: int = 0) -> str | None:
            return {"data-src": "/logos/acme.svg"}.get(attribute)

    class FakeCard:
        def query_selector_all(self, selector: str) -> list[FakeImage]:
            return [FakeImage()]

    assert (
        _extract_company_logo(FakeCard(), "https://jobsgo.vn")
        == "https://jobsgo.vn/logos/acme.svg"
    )


def test_ranking_keeps_a_source_provided_company_logo() -> None:
    ranked = rank_jobs(
        [_job("logo")],
        target_roles=["Frontend Developer"],
        skills=["React", "TypeScript"],
        seniority="junior",
        location="Hà Nội",
    )

    assert ranked[0]["company_logo_url"] == "https://cdn.example.com/acme.png"
