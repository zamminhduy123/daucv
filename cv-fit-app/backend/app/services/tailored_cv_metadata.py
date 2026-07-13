import hashlib
import hmac
import os
import re
import secrets
from uuid import UUID


def issue_tailoring_entitlement(user_id: UUID, cv_text: str, jd_text: str) -> str:
    nonce = secrets.token_hex(16)
    digest = hashlib.sha256(f"{cv_text}\0{jd_text}".encode()).hexdigest()
    secret = os.environ["NEXTAUTH_SECRET"].encode()
    signature = hmac.new(
        secret, f"{user_id}:{nonce}:{digest}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{nonce}.{digest}.{signature}"


def verify_tailoring_entitlement(
    entitlement: str, user_id: UUID, cv_text: str, jd_text: str
) -> str:
    try:
        nonce, supplied_digest, supplied_signature = entitlement.split(".", 2)
    except ValueError as exc:
        raise ValueError("Invalid tailoring entitlement") from exc
    expected_digest = hashlib.sha256(f"{cv_text}\0{jd_text}".encode()).hexdigest()
    secret = os.environ["NEXTAUTH_SECRET"].encode()
    expected_signature = hmac.new(
        secret,
        f"{user_id}:{nonce}:{expected_digest}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(
        supplied_digest, expected_digest
    ) or not hmac.compare_digest(supplied_signature, expected_signature):
        raise ValueError("Invalid tailoring entitlement")
    return hashlib.sha256(entitlement.encode()).hexdigest()


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
