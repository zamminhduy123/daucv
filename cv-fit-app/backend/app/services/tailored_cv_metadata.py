import re


def extract_target_metadata(jd_text: str) -> tuple[str | None, str | None]:
    """Extract conservative role/company labels from common JD headers."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in jd_text.splitlines()]
    lines = [line for line in lines if line][:12]
    role: str | None = None
    company: str | None = None
    for line in lines:
        key, separator, value = line.partition(":")
        normalized_key = key.strip().lower()
        if separator and normalized_key in {
            "job title",
            "title",
            "position",
            "role",
            "vị trí",
            "chức danh",
        }:
            role = value.strip() or role
        elif separator and normalized_key in {
            "company",
            "company name",
            "employer",
            "công ty",
            "doanh nghiệp",
        }:
            company = value.strip() or company

    if not role and lines:
        first = lines[0]
        if len(first) <= 100 and not first.endswith((".", ";")):
            role = first
    return role, company
