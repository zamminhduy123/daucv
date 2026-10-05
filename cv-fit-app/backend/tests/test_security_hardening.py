"""Regression tests for the 2026-10-04 security hardening pass."""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import asyncpg
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core import config
from app.core.config import NEXTAUTH_SECRET, is_mock_billing_enabled
from app.core.db import Database
from app.core.rate_limit import SlidingWindowRateLimiter
from app.dependencies import (
    DuplicateCreditReferenceError,
    add_credits,
    get_current_user,
    require_admin,
)
from app.main import create_app
from app.utils.upload_validation import looks_like_pdf

USER_ID = "12345678-1234-1234-1234-123456789012"

WRITER_BODY = {
    "cv_text": "Software Engineer CV",
    "writing_type": "email",
    "tone": "Chuyên nghiệp",
    "language": "vi",
}
FINISH_BODY = {
    "cv_text": "CV",
    "chat_history": [{"role": "user", "content": "hi"}],
    "interview_type": "general",
    "jd_text": "",
}


@pytest.fixture
def unauth_client():
    """App with the REAL get_current_user (no override, lifespan not started)."""
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# 1. Authentication on previously public LLM/TTS routes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/interview/finish", FINISH_BODY),
        ("/api/writer/generate", WRITER_BODY),
        ("/api/interview/tts", {"text": "Xin chào"}),
    ],
)
def test_llm_and_tts_routes_require_auth(
    unauth_client: TestClient, path: str, body: dict
) -> None:
    with patch(
        "app.api.routes.user.call_llm_with_fallback", new_callable=AsyncMock
    ) as llm:
        resp = unauth_client.post(path, json=body)
        bad = unauth_client.post(
            path, json=body, headers={"Authorization": "Bearer not-a-jwt"}
        )
    assert resp.status_code == 401
    assert bad.status_code == 401
    llm.assert_not_called()


def test_tts_streams_from_memory_and_caps_length(client: TestClient) -> None:
    class FakeCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            self.text = text

        async def stream(self):
            yield {"type": "WordBoundary", "offset": 0}
            yield {"type": "audio", "data": b"ID3"}
            yield {"type": "audio", "data": b"-mp3"}

    with (
        patch("app.api.routes.user.edge_tts.Communicate", FakeCommunicate),
        patch("tempfile.NamedTemporaryFile") as tmp,
    ):
        resp = client.post("/api/interview/tts", json={"text": "Câu hỏi 1"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == b"ID3-mp3"
    tmp.assert_not_called()

    too_long = client.post("/api/interview/tts", json={"text": "a" * 3001})
    assert too_long.status_code == 422


def test_tts_failure_does_not_leak_exception_text(client: TestClient) -> None:
    class BoomCommunicate:
        def __init__(self, *_: Any) -> None:
            pass

        async def stream(self):
            raise RuntimeError("edge-internal-token-xyz")
            yield  # pragma: no cover

    with patch("app.api.routes.user.edge_tts.Communicate", BoomCommunicate):
        resp = client.post("/api/interview/tts", json={"text": "hello"})
    assert resp.status_code == 500
    assert "edge-internal-token-xyz" not in resp.text


# ---------------------------------------------------------------------------
# 2. Admin protection + removed debug routes
# ---------------------------------------------------------------------------


def test_admin_metrics_requires_auth(unauth_client: TestClient) -> None:
    assert unauth_client.get("/api/admin/metrics").status_code == 401


def test_admin_metrics_forbidden_for_non_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    assert client.get("/api/admin/metrics").status_code == 403
    monkeypatch.setenv("ADMIN_EMAILS", "boss@daucv.com, other@daucv.com")
    assert client.get("/api/admin/metrics").status_code == 403


def test_admin_metrics_allowed_for_listed_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("ADMIN_EMAILS", "boss@daucv.com, Test@Example.com")
    monkeypatch.setattr("app.api.routes.admin.LOGS_DIR", tmp_path)
    resp = client.get("/api/admin/metrics")
    assert resp.status_code == 200
    assert resp.json()["total_requests"] == 0


async def test_require_admin_empty_allowlist_means_nobody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_EMAILS", "")
    with pytest.raises(HTTPException) as exc:
        await require_admin({"email": "anyone@daucv.com"})
    assert exc.value.status_code == 403
    monkeypatch.setenv("ADMIN_EMAILS", "ADMIN@daucv.com")
    assert await require_admin({"email": "admin@DAUCV.com"}) == {
        "email": "admin@DAUCV.com"
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/billing/debug-imports"),
        ("get", "/api/billing/debug-db"),
        ("post", "/api/billing/test-request"),
    ],
)
def test_debug_and_test_routes_removed(
    client: TestClient, method: str, path: str
) -> None:
    resp = getattr(client, method)(path)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. Billing hardening
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("env", "flag", "expected"),
    [
        ("development", None, False),  # off by default
        ("development", "false", False),
        ("development", "true", True),
        ("production", "true", False),
        ("staging", "true", False),
    ],
)
def test_mock_billing_gate(
    monkeypatch: pytest.MonkeyPatch, env: str, flag: str | None, expected: bool
) -> None:
    monkeypatch.setenv("ENV", env)
    if flag is None:
        monkeypatch.delenv("ALLOW_MOCK_BILLING", raising=False)
    else:
        monkeypatch.setenv("ALLOW_MOCK_BILLING", flag)
    assert is_mock_billing_enabled() is expected


def test_mock_confirm_disabled_by_default(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("ALLOW_MOCK_BILLING", raising=False)
    with patch(
        "app.api.routes.billing.add_credits", new_callable=AsyncMock
    ) as add_mock:
        resp = client.post(
            "/api/billing/mock-confirm",
            json={"package_id": "pro", "amount": 35000, "credits_to_add": 50},
        )
        buy = client.post("/api/billing/buy-credits", json={"package_id": "pro"})
    assert resp.status_code == 403
    assert buy.status_code == 403
    add_mock.assert_not_called()


def test_mock_confirm_works_only_when_explicitly_enabled_in_dev(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ALLOW_MOCK_BILLING", "true")
    with patch(
        "app.api.routes.billing.add_credits", new_callable=AsyncMock, return_value=60
    ):
        resp = client.post(
            "/api/billing/mock-confirm",
            json={"package_id": "pro", "amount": 35000, "credits_to_add": 50},
        )
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "new_credits": 60}


def _approval_url(user_id: str, package_id: str, ts: int) -> str:
    from app.api.routes.billing import sign_approval

    sig = sign_approval(user_id, package_id, ts)
    return (
        "/api/billing/approve-manual-payment"
        f"?user_id={user_id}&package_id={package_id}&timestamp={ts}&sig={sig}"
    )


def test_approval_rejects_non_uuid_user_id(client: TestClient) -> None:
    with patch(
        "app.api.routes.billing.add_credits", new_callable=AsyncMock
    ) as add_mock:
        resp = client.get(_approval_url("not-a-uuid", "pro", int(time.time())))
    assert resp.status_code == 400
    add_mock.assert_not_called()


def test_approval_rejects_non_ascii_signature(client: TestClient) -> None:
    ts = int(time.time())
    resp = client.get(
        "/api/billing/approve-manual-payment"
        f"?user_id={USER_ID}&package_id=pro&timestamp={ts}&sig=%C3%A9%C3%A9"
    )
    assert resp.status_code == 403


def test_approval_error_page_hides_exception_text(client: TestClient) -> None:
    with patch(
        "app.api.routes.billing.add_credits",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db.internal:5432 password=hunter2"),
    ):
        resp = client.get(_approval_url(USER_ID, "pro", int(time.time())))
    assert resp.status_code == 500
    assert "hunter2" not in resp.text
    assert "db.internal" not in resp.text


def test_approval_secret_prefers_dedicated_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routes import billing

    monkeypatch.setattr(billing, "BILLING_APPROVAL_SECRET", "dedicated-secret")
    assert billing._approval_secret() == "dedicated-secret"
    monkeypatch.setattr(billing, "BILLING_APPROVAL_SECRET", "")
    assert billing._approval_secret() == NEXTAUTH_SECRET


async def test_telegram_notification_uses_async_client_and_escapes_html(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import billing

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    sent: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200
        text = "ok"

    async def fake_post(self, url, *args, **kwargs):
        sent["url"] = url
        sent["json"] = kwargs["json"]
        return FakeResponse()

    user = {"id": USER_ID, "email": "<b>x</b>@evil.com", "credits": 10}
    with patch("httpx.AsyncClient.post", new=fake_post):
        result = await billing.request_manual_payment(
            billing.BuyCreditsRequest(package_id="pro"), user=user
        )
    assert result["success"] is True
    assert "<b>x</b>@evil.com" not in sent["json"]["text"]
    assert "&lt;b&gt;x&lt;/b&gt;@evil.com" in sent["json"]["text"]


# --- add_credits idempotency (dedup + credit in ONE transaction) -----------


class _FakeLedger:
    """In-memory stand-in for the users/credit_transactions tables.

    Emulates the row lock taken by ``SELECT ... FOR UPDATE`` (held until the
    transaction ends), commit-on-success, and the unique index on reference.
    """

    def __init__(self, credits: int = 10) -> None:
        self.credits = credits
        self.refs: set[str] = set()
        self.row_lock = asyncio.Lock()
        self.ledger_inserts: list[tuple] = []
        # When True the in-transaction SELECT cannot see existing references
        # (e.g. a writer it did not serialise with), so only the unique index
        # can catch the duplicate.
        self.hide_refs_from_select = False

    @property
    def pool(self):
        ledger = self

        class Conn:
            def __init__(self) -> None:
                self.holds_lock = False
                self.pending_credits: int | None = None
                self.pending_refs: set[str] = set()
                self.pending_inserts: list[tuple] = []

            async def fetchrow(self, query: str, *args):
                await asyncio.sleep(0)
                if "FOR UPDATE" in query:
                    await ledger.row_lock.acquire()
                    self.holds_lock = True
                    return {"credits": ledger.credits}
                if "reference = $1" in query:
                    if ledger.hide_refs_from_select:
                        return None
                    return {"?column?": 1} if args[0] in ledger.refs else None
                raise AssertionError(query)

            async def execute(self, query: str, *args):
                await asyncio.sleep(0)
                if query.startswith("UPDATE public.users"):
                    self.pending_credits = args[0]
                elif query.startswith("INSERT INTO public.credit_transactions"):
                    if len(args) == 5:
                        ref = args[4]
                        if ref in ledger.refs or ref in self.pending_refs:
                            raise asyncpg.exceptions.UniqueViolationError("dup")
                        self.pending_refs.add(ref)
                    self.pending_inserts.append(args)
                return "OK"

            def transaction(self):
                conn = self

                class Tx:
                    async def __aenter__(self):
                        return conn

                    async def __aexit__(self, exc_type, exc, tb):
                        if exc_type is None:
                            if conn.pending_credits is not None:
                                ledger.credits = conn.pending_credits
                            ledger.refs |= conn.pending_refs
                            ledger.ledger_inserts += conn.pending_inserts
                        if conn.holds_lock:
                            ledger.row_lock.release()
                        return False

                return Tx()

        class Acquire:
            async def __aenter__(self):
                return Conn()

            async def __aexit__(self, *exc):
                return False

        class Pool:
            def acquire(self):
                return Acquire()

        return Pool()


async def test_add_credits_concurrent_duplicate_reference_credits_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = _FakeLedger(credits=10)
    monkeypatch.setattr(Database, "pool", ledger.pool)

    async def approve():
        return await add_credits(
            user_id=USER_ID,
            amount=50,
            tx_type="purchase",
            description="manual",
            reference="INV_x_pro_1",
        )

    results = await asyncio.gather(
        approve(), approve(), approve(), return_exceptions=True
    )
    successes = [r for r in results if isinstance(r, int)]
    duplicates = [r for r in results if isinstance(r, DuplicateCreditReferenceError)]
    assert successes == [60]
    assert len(duplicates) == 2
    assert ledger.credits == 60
    assert len(ledger.ledger_inserts) == 1
    assert ledger.ledger_inserts[0][4] == "INV_x_pro_1"


async def test_add_credits_maps_unique_violation_to_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = _FakeLedger(credits=10)
    ledger.refs.add("INV_dup")
    ledger.hide_refs_from_select = True
    monkeypatch.setattr(Database, "pool", ledger.pool)

    with pytest.raises(DuplicateCreditReferenceError):
        await add_credits(
            user_id=USER_ID,
            amount=5,
            tx_type="purchase",
            description="manual",
            reference="INV_dup",
        )
    # Transaction rolled back: balance unchanged, nothing inserted.
    assert ledger.credits == 10
    assert ledger.ledger_inserts == []


async def test_add_credits_without_reference_keeps_legacy_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = _FakeLedger(credits=1)
    monkeypatch.setattr(Database, "pool", ledger.pool)
    assert await add_credits(USER_ID, 2, "refund", "r") == 3
    assert await add_credits(USER_ID, 2, "refund", "r") == 5
    assert all(len(args) == 4 for args in ledger.ledger_inserts)


# ---------------------------------------------------------------------------
# 4. Internal error details are not returned to clients
# ---------------------------------------------------------------------------


async def test_get_current_user_db_error_is_generic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = jwt.encode(
        {"email": "new@daucv.com", "name": "New", "exp": int(time.time()) + 600},
        NEXTAUTH_SECRET,
        algorithm="HS256",
    )
    monkeypatch.setattr(Database, "fetch_one", AsyncMock(return_value=None))
    monkeypatch.setattr(
        Database,
        "execute",
        AsyncMock(side_effect=RuntimeError("host=db.internal password=hunter2")),
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(authorization=f"Bearer {token}")
    assert exc.value.status_code == 500
    assert "hunter2" not in str(exc.value.detail)
    assert "db.internal" not in str(exc.value.detail)


def test_writer_llm_error_does_not_leak(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*args: Any, **kwargs: Any):
        raise RuntimeError("provider-key sk-live-123")

    monkeypatch.setattr("app.api.routes.user.call_llm_with_fallback", boom)
    resp = client.post("/api/writer/generate", json=WRITER_BODY)
    assert resp.status_code == 502
    assert "sk-live-123" not in resp.text


# ---------------------------------------------------------------------------
# 5. LLM input log gating + sanitization
# ---------------------------------------------------------------------------


@pytest.fixture
def llm_log_dirs(tmp_path, monkeypatch: pytest.MonkeyPatch):
    from app.utils import llm_logger

    prompts = tmp_path / "prompts"
    prompts.mkdir()
    monkeypatch.setattr(llm_logger, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(llm_logger, "PROMPTS_DIR", prompts)
    return tmp_path


def _log_input() -> str:
    from app.utils.llm_logger import log_llm_input

    return log_llm_input(
        feature="writing_assistant",
        provider="Remote-Qwen",
        model="m",
        system_prompt="You are helpful.",
        user_content="CV: Nguyen Van A, a.nguyen@gmail.com, 0912345678",
    )


def test_llm_input_logging_off_outside_development(
    llm_log_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("LOG_LLM_INPUTS", raising=False)
    assert _log_input() == ""
    assert list(llm_log_dirs.rglob("*.*")) == []


def test_llm_input_logging_sanitizes_when_enabled(
    llm_log_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("LOG_LLM_INPUTS", "true")
    path = _log_input()
    assert path
    written = "".join(p.read_text(encoding="utf-8") for p in llm_log_dirs.rglob("*.*"))
    assert "a.nguyen@gmail.com" not in written
    assert "0912345678" not in written
    assert "[REDACTED-PII]" in written


@pytest.mark.parametrize("env", ["development", "production", None])
def test_llm_input_logging_off_by_default_everywhere(
    llm_log_dirs, monkeypatch: pytest.MonkeyPatch, env: str | None
) -> None:
    if env is None:
        monkeypatch.delenv("ENV", raising=False)
    else:
        monkeypatch.setenv("ENV", env)
    monkeypatch.delenv("LOG_LLM_INPUTS", raising=False)
    assert config.llm_input_logging_enabled() is False
    assert _log_input() == ""
    monkeypatch.setenv("LOG_LLM_INPUTS", "true")
    assert config.llm_input_logging_enabled() is True


# ---------------------------------------------------------------------------
# 6. Rate limiting
# ---------------------------------------------------------------------------


def test_sliding_window_limiter_unit() -> None:
    now = [1000.0]
    limiter = SlidingWindowRateLimiter(60, clock=lambda: now[0])
    assert limiter.hit("llm", "u1", 2) is None
    now[0] += 1
    assert limiter.hit("llm", "u1", 2) is None
    now[0] += 1
    retry = limiter.hit("llm", "u1", 2)
    assert retry == pytest.approx(58.0)
    # other users / groups are independent
    assert limiter.hit("llm", "u2", 2) is None
    assert limiter.hit("pdf", "u1", 2) is None
    now[0] = 1060.5  # first hit has left the window
    assert limiter.hit("llm", "u1", 2) is None
    assert limiter.hit("llm", "u1", 2) is not None


def test_rate_limit_returns_429_with_retry_after(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models.responses import WriterResponse

    async def fake_llm(*args: Any, **kwargs: Any) -> WriterResponse:
        return WriterResponse(subject_line="s", content="c", tips=[])

    monkeypatch.setattr("app.api.routes.user.call_llm_with_fallback", fake_llm)
    monkeypatch.setitem(config.RATE_LIMITS_PER_WINDOW, "llm", 2)

    codes = [
        client.post("/api/writer/generate", json=WRITER_BODY).status_code
        for _ in range(2)
    ]
    limited = client.post("/api/writer/generate", json=WRITER_BODY)
    assert codes == [200, 200]
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    # A different route group is not affected.
    assert client.post("/api/interview/tts", json={"text": ""}).status_code == 400


def test_rate_limit_can_be_disabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models.responses import WriterResponse

    async def fake_llm(*args: Any, **kwargs: Any) -> WriterResponse:
        return WriterResponse(subject_line="s", content="c", tips=[])

    monkeypatch.setattr("app.api.routes.user.call_llm_with_fallback", fake_llm)
    monkeypatch.setitem(config.RATE_LIMITS_PER_WINDOW, "llm", 1)
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", False)
    for _ in range(3):
        assert client.post("/api/writer/generate", json=WRITER_BODY).status_code == 200


# ---------------------------------------------------------------------------
# 7. PDF magic bytes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "ok"),
    [
        (b"%PDF-1.7\n...", True),
        (b"\xef\xbb\xbf%PDF-1.4", True),
        (b"\r\n  %PDF-1.4", True),
        (b"junk-prefix\n%PDF-1.4", True),
        (b"<html><script>alert(1)</script>", False),
        (b"x" * 1024 + b"%PDF-1.4", False),
        (b"", False),
    ],
)
def test_looks_like_pdf(data: bytes, ok: bool) -> None:
    assert looks_like_pdf(data) is ok


def test_extract_pdf_rejects_spoofed_content_type(client: TestClient) -> None:
    with patch("app.api.routes.user.extract_cv_content_blocks") as extract_blocks:
        resp = client.post(
            "/api/extract-pdf",
            data={"purpose": "cv"},
            files={"file": ("cv.pdf", b"<html>not a pdf</html>", "application/pdf")},
        )
    assert resp.status_code == 415
    extract_blocks.assert_not_called()


def test_upload_and_match_rejects_spoofed_pdf_before_charging(
    client: TestClient,
) -> None:
    with (
        patch("app.api.routes.user.extract_text_from_pdf") as extract_text,
        patch("app.api.routes.user.reserve_credits", new_callable=AsyncMock) as reserve,
    ):
        resp = client.post(
            "/api/upload-and-match",
            data={"jd_text": "JD"},
            files={"cv_file": ("cv.pdf", b"MZ\x90\x00binary", "application/pdf")},
        )
    assert resp.status_code == 415
    extract_text.assert_not_called()
    reserve.assert_not_called()


def test_upload_and_match_enforces_size_after_read(client: TestClient) -> None:
    with (
        patch("app.api.routes.user.PDF_MAX_SIZE", 8),
        patch("app.api.routes.user.extract_text_from_pdf") as extract_text,
    ):
        resp = client.post(
            "/api/upload-and-match",
            data={"jd_text": "JD"},
            files={"cv_file": ("cv.pdf", b"%PDF-1.7-oversize", "application/pdf")},
        )
    assert resp.status_code == 413
    extract_text.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Crawler SSRF guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://itviec.com/it-jobs?q=python&city=", True),
        ("https://ybox.vn/api/v1/post?search=x", True),
        ("http://itviec.com/it-jobs", False),
        ("https://169.254.169.254/latest/meta-data", False),
        ("https://itviec.com.evil.example/", False),
        ("file:///etc/passwd", False),
        ("https://localhost:8000/", False),
    ],
)
def test_crawler_fetch_allowlist(url: str, ok: bool) -> None:
    from app.services.job_crawler import _is_allowed_fetch_url

    assert _is_allowed_fetch_url(url) is ok


def test_crawler_query_injection_cannot_change_host() -> None:
    from app.services.job_crawler import SEARCH_URLS, _is_allowed_fetch_url

    hostile = "x@169.254.169.254/#"
    for template in SEARCH_URLS.values():
        url = template.format(query=hostile, city=hostile)
        assert _is_allowed_fetch_url(url)


async def test_navigate_refuses_disallowed_url() -> None:
    from app.services.job_crawler import _navigate

    page = AsyncMock()
    assert await _navigate(page, "http://127.0.0.1:5432/") is False
    page.goto.assert_not_called()


# ---------------------------------------------------------------------------
# Follow-up review fixes (2026-10-05)
# ---------------------------------------------------------------------------


def test_describe_exception_omits_validation_input() -> None:
    from pydantic import BaseModel

    from app.utils.error_summary import describe_exception

    class Model(BaseModel):
        score: int

    secret = "Nguyen Van A worked at Secret Corp"
    try:
        Model.model_validate({"score": secret})
    except Exception as exc:  # noqa: BLE001
        summary = describe_exception(exc)
    assert summary.startswith("ValidationError(1 errors: score:")
    assert secret not in summary


def test_describe_exception_truncates_long_messages() -> None:
    from app.utils.error_summary import describe_exception

    summary = describe_exception(RuntimeError("cv " * 500))
    assert summary.startswith("RuntimeError: cv")
    assert len(summary) < 260


def test_llm_failure_log_has_no_cv_text(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    leaked = "CANDIDATE-CV-BODY-" * 30
    with (
        patch(
            "app.api.routes.user.call_llm_with_fallback",
            AsyncMock(side_effect=RuntimeError(leaked)),
        ),
        caplog.at_level("INFO"),
    ):
        resp = client.post("/api/writer/generate", json=WRITER_BODY)
    assert resp.status_code == 502
    assert "writer_generate: LLM call failed: RuntimeError" in caplog.text
    assert leaked not in caplog.text


@pytest.mark.parametrize(
    ("env", "link_logged"), [("production", False), ("development", True)]
)
def test_undelivered_payment_request_logs_link_only_in_development(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    env: str,
    link_logged: bool,
) -> None:
    monkeypatch.setenv("ENV", env)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with caplog.at_level("INFO"):
        resp = client.post(
            "/api/billing/request-manual-payment", json={"package_id": "pro"}
        )
    assert resp.status_code == 200
    assert ("sig=" in caplog.text) is link_logged
    if not link_logged:
        assert "NOT delivered to Telegram" in caplog.text


def test_build_approval_url_round_trips_through_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from urllib.parse import parse_qs, urlparse

    from app.api.routes.billing import build_approval_url, sign_approval

    monkeypatch.setenv("BASE_URL", "https://example.test")
    url = build_approval_url(USER_ID, "pro", 1_700_000_000)
    parsed = urlparse(url)
    qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert parsed.netloc == "example.test"
    assert qs["sig"] == sign_approval(USER_ID, "pro", 1_700_000_000)


# ---------------------------------------------------------------------------
# Second review follow-ups (2026-10-05)
# ---------------------------------------------------------------------------


async def test_all_providers_failed_detail_hides_last_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import BaseModel

    from app.services import ai_service

    class Out(BaseModel):
        ok: bool

    class FailingProvider:
        name = "Fake"
        model = "fake-model"
        is_configured = True
        max_output_tokens = 100

        async def generate_structured(self, **_: Any):
            raise RuntimeError(
                "ConnectError: http://10.1.2.3:8080/v1/chat/completions refused"
            )

    monkeypatch.setattr(ai_service.config, "PROVIDERS", [FailingProvider()])
    monkeypatch.setattr(ai_service, "log_llm_input", lambda **_: "")
    monkeypatch.setattr(ai_service, "log_llm_request", lambda *_: None)
    monkeypatch.setattr(ai_service.asyncio, "sleep", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        await ai_service.call_llm_with_fallback(
            "Return JSON", "cv text", Out, max_retries=1
        )
    assert exc.value.status_code == 503
    assert "overloaded" in str(exc.value.detail)
    assert "10.1.2.3" not in str(exc.value.detail)
    assert "8080" not in str(exc.value.detail)


async def test_jwt_without_exp_is_rejected() -> None:
    token = jwt.encode({"email": "a@daucv.com"}, NEXTAUTH_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    "phone",
    [
        "0912345678",
        "0912 345 678",
        "091 234 5678",
        "0912.345.678",
        "0912-345-678",
        "+84 912 345 678",
        "+84912345678",
        "024 3826 4567",
    ],
)
def test_sanitizer_masks_vn_phone_groupings(phone: str) -> None:
    from app.utils.pii_sanitizer import sanitize

    out = sanitize(f"Liên hệ: {phone}.")
    assert "[REDACTED-PII]" in out
    assert phone not in out


@pytest.mark.parametrize("text", ["2019 - 2023", "05.10.2026", "GPA 3.8/4.0"])
def test_sanitizer_leaves_dates_and_years(text: str) -> None:
    from app.utils.pii_sanitizer import sanitize

    assert sanitize(text) == text


def test_range_plan_section_log_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from app.services import cv_range_plan_service

    monkeypatch.delenv("LOG_LLM_INPUTS", raising=False)
    monkeypatch.setattr(cv_range_plan_service, "LOGS_DIR", tmp_path)
    # Returns before touching the section when logging is off.
    cv_range_plan_service._log_section_to_file(None)  # type: ignore[arg-type]
    assert list(tmp_path.iterdir()) == []


def test_wysiwyg_html_gets_no_subresource_csp() -> None:
    from app.services.cv_export_service import sanitize_wysiwyg_html
    from app.utils.render_isolation import NO_SUBRESOURCE_CSP_META

    clean = sanitize_wysiwyg_html(
        '<html><head><style>p{background:url("file:///etc/passwd")}</style>'
        "</head><body><p>Hi</p></body></html>"
    )
    assert clean.startswith("<html><head>" + NO_SUBRESOURCE_CSP_META)
    assert "default-src 'none'" in clean


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("data:font/woff2;base64,AAAA", True),
        ("about:blank", True),
        ("file:///etc/passwd", False),
        ("http://169.254.169.254/latest/meta-data", False),
        ("https://fonts.googleapis.com/css", False),
        ("chrome://settings", False),
    ],
)
def test_render_request_allowlist(url: str, ok: bool) -> None:
    from app.utils.render_isolation import is_allowed_render_request

    assert is_allowed_render_request(url) is ok


async def test_block_non_inline_requests_aborts_file_urls() -> None:
    from types import SimpleNamespace

    from app.utils.render_isolation import block_non_inline_requests

    route = SimpleNamespace(
        request=SimpleNamespace(url="file:///etc/passwd"),
        abort=AsyncMock(),
        continue_=AsyncMock(),
    )
    await block_non_inline_requests(route)
    route.abort.assert_awaited_once()
    route.continue_.assert_not_awaited()
