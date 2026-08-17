import hashlib
import hmac
import json
import os
import re
import secrets
import time
from uuid import UUID

from app.models.cv_document_v2 import CVDocumentV2, CVTailoringDiagnostics


def issue_tailoring_entitlement(user_id: UUID, cv_text: str, jd_text: str) -> str:
    nonce = secrets.token_hex(16)
    digest = hashlib.sha256(f"{cv_text}\0{jd_text}".encode()).hexdigest()
    secret = os.environ["NEXTAUTH_SECRET"].encode()
    signature = hmac.new(
        secret,
        f"{user_id}:{nonce}:{digest}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{nonce}.{digest}.{signature}"


def verify_tailoring_entitlement(
    entitlement: str,
    user_id: UUID,
    cv_text: str,
    jd_text: str,
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
        supplied_digest,
        expected_digest,
    ) or not hmac.compare_digest(supplied_signature, expected_signature):
        raise ValueError("Invalid tailoring entitlement")
    return hashlib.sha256(entitlement.encode()).hexdigest()


def canonical_source_document_hash(document: CVDocumentV2) -> str:
    """Deterministic hash of the source document for entitlement binding."""
    canonical = document.model_dump(mode="json")
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def issue_pipeline_source_ticket(
    user_id: UUID,
    source_text: str,
    source_document: CVDocumentV2,
    raw_extraction_ref_id: str | None,
) -> str:
    """Sign the successful LLM #1 source document for later LLM #3 persistence."""
    nonce = secrets.token_hex(16)
    analysis_key = secrets.token_hex(16)
    issued_at = int(time.time())
    expires_at = issued_at + 86400
    source_text_hash = hashlib.sha256(source_text.encode()).hexdigest()
    document_hash = canonical_source_document_hash(source_document)
    raw_ref = raw_extraction_ref_id or ""
    secret = os.environ["NEXTAUTH_SECRET"].encode()
    message = (
        f"{user_id}:{nonce}:{analysis_key}:{issued_at}:{expires_at}:"
        f"{source_text_hash}:{document_hash}:{raw_ref}"
    )
    signature = hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()
    return (
        f"p1.{nonce}.{analysis_key}.{issued_at}.{expires_at}."
        f"{source_text_hash}.{document_hash}.{raw_ref}.{signature}"
    )


def verify_pipeline_source_ticket(
    ticket: str,
    user_id: UUID,
    source_text: str,
    source_document: CVDocumentV2,
    raw_extraction_ref_id: str | None,
) -> str:
    """Verify source ownership, freshness, and document integrity for export."""
    try:
        (
            version,
            nonce,
            analysis_key,
            issued_at_raw,
            expires_at_raw,
            supplied_source_text_hash,
            supplied_document_hash,
            supplied_raw_ref,
            supplied_signature,
        ) = ticket.split(".", 8)
        issued_at = int(issued_at_raw)
        expires_at = int(expires_at_raw)
    except (ValueError, IndexError) as exc:
        raise ValueError("Invalid pipeline source ticket") from exc
    if version != "p1" or not nonce or not analysis_key:
        raise ValueError("Invalid pipeline source ticket")
    now = int(time.time())
    if issued_at > now + 300 or expires_at <= now or expires_at - issued_at > 86400:
        raise ValueError("Pipeline source ticket has expired")

    expected_source_text_hash = hashlib.sha256(source_text.encode()).hexdigest()
    expected_document_hash = canonical_source_document_hash(source_document)
    expected_raw_ref = raw_extraction_ref_id or ""
    if not (
        hmac.compare_digest(supplied_source_text_hash, expected_source_text_hash)
        and hmac.compare_digest(supplied_document_hash, expected_document_hash)
        and hmac.compare_digest(supplied_raw_ref, expected_raw_ref)
    ):
        raise ValueError("Pipeline source ticket no longer matches this CV")
    secret = os.environ["NEXTAUTH_SECRET"].encode()
    message = (
        f"{user_id}:{nonce}:{analysis_key}:{issued_at}:{expires_at}:"
        f"{expected_source_text_hash}:{expected_document_hash}:{expected_raw_ref}"
    )
    expected_signature = hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise ValueError("Invalid pipeline source ticket")
    return analysis_key


def issue_tailoring_entitlement_v2(
    user_id: UUID,
    cv_text: str,
    jd_text: str,
    source_document: CVDocumentV2,
) -> str:
    """Issue a V2 entitlement that also binds the server-produced source document."""
    nonce = secrets.token_hex(16)
    input_digest = hashlib.sha256(f"{cv_text}\0{jd_text}".encode()).hexdigest()
    doc_digest = canonical_source_document_hash(source_document)
    secret = os.environ["NEXTAUTH_SECRET"].encode()
    signature = hmac.new(
        secret,
        f"{user_id}:{nonce}:{input_digest}:{doc_digest}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"v2.{nonce}.{input_digest}.{doc_digest}.{signature}"


def verify_tailoring_entitlement_v2(
    entitlement: str,
    user_id: UUID,
    cv_text: str,
    jd_text: str,
    source_document: CVDocumentV2,
) -> str:
    """Verify a V2 entitlement including source document hash."""
    try:
        (
            version,
            nonce,
            supplied_input_digest,
            supplied_doc_digest,
            supplied_signature,
        ) = entitlement.split(".", 4)
    except ValueError as exc:
        raise ValueError("Invalid tailoring entitlement") from exc
    if version != "v2":
        raise ValueError("Invalid tailoring entitlement")
    expected_input_digest = hashlib.sha256(f"{cv_text}\0{jd_text}".encode()).hexdigest()
    expected_doc_digest = canonical_source_document_hash(source_document)
    secret = os.environ["NEXTAUTH_SECRET"].encode()
    expected_signature = hmac.new(
        secret,
        f"{user_id}:{nonce}:{expected_input_digest}:{expected_doc_digest}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(supplied_input_digest, expected_input_digest):
        raise ValueError("Invalid tailoring entitlement")
    if not hmac.compare_digest(supplied_doc_digest, expected_doc_digest):
        raise ValueError("Invalid tailoring entitlement")
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise ValueError("Invalid tailoring entitlement")
    return hashlib.sha256(entitlement.encode()).hexdigest()


def issue_tailoring_entitlement_v3(
    user_id: UUID,
    cv_text: str,
    jd_text: str,
    source_document: CVDocumentV2,
    tailored_document: CVDocumentV2,
    diagnostics: CVTailoringDiagnostics,
    *,
    analysis_key: str | None = None,
) -> str:
    """Issue a short-lived V3 entitlement bound to every authoritative input."""
    nonce = secrets.token_hex(16)
    analysis_key = analysis_key or secrets.token_hex(16)
    issued_at = int(time.time())
    expires_at = issued_at + 86400

    input_digest = hashlib.sha256(f"{cv_text}\0{jd_text}".encode()).hexdigest()
    source_hash = canonical_source_document_hash(source_document)
    tailored_hash = canonical_source_document_hash(tailored_document)
    jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest() if jd_text else ""

    if (
        diagnostics.source_document_hash != source_hash
        or diagnostics.jd_hash != jd_hash
    ):
        raise ValueError("Tailoring diagnostics do not match entitlement inputs")
    accepted_ops_digest = _accepted_operations_digest(diagnostics)
    diag_hash = _canonical_model_hash(diagnostics)
    rewrite_version = diagnostics.rewrite_version

    secret = os.environ["NEXTAUTH_SECRET"].encode()
    msg = _v3_signature_message(
        user_id=user_id,
        nonce=nonce,
        analysis_key=analysis_key,
        issued_at=issued_at,
        expires_at=expires_at,
        input_digest=input_digest,
        source_hash=source_hash,
        tailored_hash=tailored_hash,
        jd_hash=jd_hash,
        diagnostics_hash=diag_hash,
        accepted_ops_digest=accepted_ops_digest,
        rewrite_version=rewrite_version,
    )
    signature = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()

    return f"v3.{nonce}.{analysis_key}.{issued_at}.{expires_at}.{input_digest}.{source_hash}.{tailored_hash}.{jd_hash}.{diag_hash}.{accepted_ops_digest}.{rewrite_version}.{signature}"


def verify_tailoring_entitlement_v3(
    entitlement: str,
    user_id: UUID,
    cv_text: str,
    jd_text: str,
    source_document: CVDocumentV2,
    tailored_document: CVDocumentV2,
    diagnostics: CVTailoringDiagnostics,
) -> str:
    """Verify all V3 claims and return its stable one-time analysis key."""
    if diagnostics is None:
        raise ValueError("Tailoring diagnostics are required")
    try:
        parts = entitlement.split(".")
        if parts[0] != "v3" or len(parts) != 13:
            raise ValueError("Invalid tailoring entitlement format")
        (
            _,
            nonce,
            analysis_key,
            issued_at_str,
            expires_at_str,
            supplied_input_digest,
            supplied_source_hash,
            supplied_tailored_hash,
            supplied_jd_hash,
            supplied_diag_hash,
            supplied_ops_digest,
            supplied_rewrite_version,
            supplied_signature,
        ) = parts
        issued_at = int(issued_at_str)
        expires_at = int(expires_at_str)
        rewrite_version = int(supplied_rewrite_version)
    except (ValueError, IndexError) as exc:
        raise ValueError("Invalid tailoring entitlement") from exc

    now = int(time.time())
    if issued_at > now + 300 or expires_at <= now:
        raise ValueError("Invalid or expired tailoring entitlement")
    if expires_at <= issued_at or expires_at - issued_at > 86400:
        raise ValueError("Invalid tailoring entitlement lifetime")
    if not nonce or not analysis_key:
        raise ValueError("Invalid tailoring entitlement")

    expected_input_digest = hashlib.sha256(f"{cv_text}\0{jd_text}".encode()).hexdigest()
    expected_source_hash = canonical_source_document_hash(source_document)
    expected_tailored_hash = canonical_source_document_hash(tailored_document)
    expected_jd_hash = (
        hashlib.sha256(jd_text.encode("utf-8")).hexdigest() if jd_text else ""
    )

    expected_ops_digest = _accepted_operations_digest(diagnostics)
    expected_diag_hash = _canonical_model_hash(diagnostics)
    if diagnostics.source_document_hash != expected_source_hash:
        raise ValueError("Invalid tailoring diagnostics source hash")
    if diagnostics.jd_hash != expected_jd_hash:
        raise ValueError("Invalid tailoring diagnostics JD hash")
    if diagnostics.rewrite_version != rewrite_version:
        raise ValueError("Invalid tailoring entitlement rewrite version")

    secret = os.environ["NEXTAUTH_SECRET"].encode()
    msg = _v3_signature_message(
        user_id=user_id,
        nonce=nonce,
        analysis_key=analysis_key,
        issued_at=issued_at,
        expires_at=expires_at,
        input_digest=expected_input_digest,
        source_hash=expected_source_hash,
        tailored_hash=expected_tailored_hash,
        jd_hash=expected_jd_hash,
        diagnostics_hash=expected_diag_hash,
        accepted_ops_digest=expected_ops_digest,
        rewrite_version=rewrite_version,
    )
    expected_signature = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()

    supplied_expected = (
        (supplied_input_digest, expected_input_digest),
        (supplied_source_hash, expected_source_hash),
        (supplied_tailored_hash, expected_tailored_hash),
        (supplied_jd_hash, expected_jd_hash),
        (supplied_diag_hash, expected_diag_hash),
        (supplied_ops_digest, expected_ops_digest),
    )
    if any(
        not hmac.compare_digest(supplied, expected)
        for supplied, expected in supplied_expected
    ):
        raise ValueError("Invalid tailoring entitlement binding")
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise ValueError("Invalid tailoring entitlement signature")

    return analysis_key


def _canonical_model_hash(model: CVTailoringDiagnostics) -> str:
    encoded = json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _accepted_operations_digest(diagnostics: CVTailoringDiagnostics) -> str:
    accepted_ops = [
        {
            "b": decision.block_id,
            "f": decision.field,
            "oh": decision.original_value_hash,
            "ph": decision.proposed_value_hash,
        }
        for decision in sorted(
            diagnostics.decisions,
            key=lambda item: (item.block_id, item.field, item.operation_id),
        )
        if decision.status == "accepted"
    ]
    encoded = json.dumps(
        accepted_ops,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _v3_signature_message(
    *,
    user_id: UUID,
    nonce: str,
    analysis_key: str,
    issued_at: int,
    expires_at: int,
    input_digest: str,
    source_hash: str,
    tailored_hash: str,
    jd_hash: str,
    diagnostics_hash: str,
    accepted_ops_digest: str,
    rewrite_version: int,
) -> str:
    claims = (
        "v3",
        str(user_id),
        nonce,
        analysis_key,
        str(issued_at),
        str(expires_at),
        input_digest,
        source_hash,
        tailored_hash,
        jd_hash,
        diagnostics_hash,
        accepted_ops_digest,
        str(rewrite_version),
    )
    return ":".join(claims)


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
