import hashlib
import hmac
import html
import logging
import os
import time
import urllib.parse
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.config import (
    BILLING_APPROVAL_SECRET,
    NEXTAUTH_SECRET,
    current_env,
    is_mock_billing_enabled,
)
from app.dependencies import (
    DuplicateCreditReferenceError,
    add_credits,
    get_current_user,
)
from app.schemas.billing import (
    BuyCreditsRequest,
    BuyCreditsResponse,
    MockPaymentConfirmRequest,
    MockPaymentConfirmResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

# Approval links expire after 7 days.
APPROVAL_LINK_TTL_SECONDS = 604800

_approval_secret_fallback_warned = False


def _approval_secret() -> str:
    """HMAC key for manual-payment approval links.

    Uses BILLING_APPROVAL_SECRET; falls back to NEXTAUTH_SECRET (warning once)
    so existing deployments keep working until the dedicated secret is set.
    """
    global _approval_secret_fallback_warned
    if BILLING_APPROVAL_SECRET:
        return BILLING_APPROVAL_SECRET
    if not _approval_secret_fallback_warned:
        logger.warning(
            "BILLING_APPROVAL_SECRET is not set; signing manual-payment approval "
            "links with NEXTAUTH_SECRET. Set a dedicated secret in production."
        )
        _approval_secret_fallback_warned = True
    return NEXTAUTH_SECRET


def sign_approval(user_id: str, package_id: str, timestamp: int) -> str:
    message = f"{user_id}:{package_id}:{timestamp}"
    return hmac.new(
        _approval_secret().encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_approval_url(
    user_id: str, package_id: str, timestamp: int, sig: str | None = None
) -> str:
    """One-click approval link for a manual payment (signed if ``sig`` is None)."""
    if sig is None:
        sig = sign_approval(user_id, package_id, timestamp)
    base_url = os.getenv("BASE_URL", "https://daucv.com")
    query = urllib.parse.urlencode(
        {
            "user_id": user_id,
            "package_id": package_id,
            "timestamp": timestamp,
            "sig": sig,
        }
    )
    return f"{base_url}/api/billing/approve-manual-payment?{query}"


def _require_mock_billing() -> None:
    if not is_mock_billing_enabled():
        raise HTTPException(
            status_code=403,
            detail="Cổng thanh toán thử nghiệm không được bật ở môi trường này.",
        )


def _html_page(message: str, status_code: int) -> HTMLResponse:
    """Minimal HTML response; ``message`` is escaped here."""
    return HTMLResponse(
        content=f"<h2>{html.escape(message)}</h2>",
        status_code=status_code,
    )


PACKAGES = {
    "starter": {"credits": 10, "price": 15000, "name": "Starter Pack"},
    "mid": {"credits": 20, "price": 24000, "name": "Mid Pack"},
    "pro": {"credits": 50, "price": 35000, "name": "Pro Pack"},
}


@router.post("/buy-credits", response_model=BuyCreditsResponse)
async def buy_credits(req: BuyCreditsRequest, user: dict = Depends(get_current_user)):
    _require_mock_billing()

    package_id = req.package_id
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Gói credit không hợp lệ.")

    package = PACKAGES[package_id]

    checkout_url = (
        f"/checkout/mock?package_id={package_id}"
        f"&amount={package['price']}"
        f"&credits={package['credits']}"
    )

    return BuyCreditsResponse(checkout_url=checkout_url)


@router.post("/mock-confirm", response_model=MockPaymentConfirmResponse)
async def mock_confirm(
    req: MockPaymentConfirmRequest,
    user: dict = Depends(get_current_user),
):
    _require_mock_billing()

    package_id = req.package_id
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Gói credit không hợp lệ.")

    package = PACKAGES[package_id]

    if req.amount != package["price"] or req.credits_to_add != package["credits"]:
        raise HTTPException(
            status_code=400,
            detail="Thông tin thanh toán không khớp với định nghĩa gói.",
        )

    try:
        new_balance = await add_credits(
            user_id=user["id"],
            amount=package["credits"],
            tx_type="purchase",
            description=f"Mua gói {package['name']} nạp {package['credits']} credits.",
        )

        logger.info(
            f"User {user['email']} successfully purchased {package['credits']} credits. New balance: {new_balance}",
        )

        return MockPaymentConfirmResponse(success=True, new_credits=new_balance)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing credit addition for user %s", user["id"])
        raise HTTPException(status_code=500, detail="Không thể cập nhật số dư.") from e


# --- Manual Billing (VietQR & Telegram one-click approval) ------------------


@router.post("/request-manual-payment")
async def request_manual_payment(
    req: BuyCreditsRequest,
    user: dict = Depends(get_current_user),
):
    package_id = req.package_id
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Gói credit không hợp lệ.")

    package = PACKAGES[package_id]
    timestamp = int(time.time())

    # HMAC-sign the approval link (BILLING_APPROVAL_SECRET; see _approval_secret)
    sig = sign_approval(str(user["id"]), package_id, timestamp)

    approve_url = build_approval_url(str(user["id"]), package_id, timestamp, sig)

    # Format Telegram Message (parse_mode=HTML, so escape interpolated values)
    safe_email = html.escape(str(user["email"]))
    safe_user_id = html.escape(str(user["id"]))
    message_text = (
        f"🔔 <b>Yêu cầu nạp tiền mới!</b>\n\n"
        f"• <b>User:</b> {safe_email} (ID: <code>{safe_user_id}</code>)\n"
        f"• <b>Gói:</b> {package['name']} ({package['credits']} credits)\n"
        f"• <b>Số tiền:</b> {package['price']:,} VND\n"
        f"• <b>Nội dung chuyển khoản:</b> <code>DAUCV {package_id.upper()} {safe_email}</code>\n\n"
        f"👉 <a href='{html.escape(approve_url, quote=True)}'>Duyệt nạp tiền (Approve)</a>"
    )

    # Send to Telegram if configured
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    sent_to_telegram = False

    if telegram_token and chat_id:
        try:
            # Async client so the event loop is never blocked on Telegram.
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message_text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
            if response.status_code == 200:
                sent_to_telegram = True
            else:
                logger.error(
                    "Telegram API responded with status %s: %s",
                    response.status_code,
                    response.text[:500],
                )
        except Exception as e:
            # Never log the exception text verbatim: httpx errors include the
            # request URL, which embeds the bot token.
            logger.error(
                "Failed to send Telegram notification: error_type=%s",
                type(e).__name__,
            )

    if not sent_to_telegram:
        if current_env() == "development":
            logger.info(
                f"\n================ TELEGRAM MOCK ALERTS ================\n"
                f"{message_text}\n"
                f"======================================================",
            )
        else:
            # The signed approval link works like a password for this top-up,
            # so it never goes into logs outside development. Regenerate it
            # with: python scripts/sign_approval_link.py <user_id> <package_id> <timestamp>
            logger.error(
                "Manual payment request NOT delivered to Telegram: "
                "user_id=%s package_id=%s timestamp=%s",
                user["id"],
                package_id,
                timestamp,
            )

    # Configure VietQR Bank Transfer Details
    bank_id = os.getenv("BANK_ID", "TCB")
    bank_account = os.getenv("BANK_ACCOUNT", "0354160401")
    bank_account_name = os.getenv("BANK_ACCOUNT_NAME", "ZAM MINH DUY")

    # Generate VietQR payment URL (compact2 template)
    payment_desc = f"DAUCV {package_id.upper()} {user['email']}"
    encoded_desc = urllib.parse.quote(payment_desc)
    encoded_name = urllib.parse.quote(bank_account_name)
    qr_url = (
        f"https://img.vietqr.io/image/{bank_id}-{bank_account}-compact2.png"
        f"?amount={package['price']}&addInfo={encoded_desc}&accountName={encoded_name}"
    )

    return {
        "success": True,
        "bank_id": bank_id,
        "bank_account": bank_account,
        "bank_account_name": bank_account_name,
        "amount": package["price"],
        "description": payment_desc,
        "qr_url": qr_url,
    }


@router.get("/approve-manual-payment", response_class=HTMLResponse)
async def approve_manual_payment(
    user_id: str,
    package_id: str,
    timestamp: int,
    sig: str,
):
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Gói credit không hợp lệ.")

    # Replay Protection: Link expires after 7 days (604800 seconds)
    current_time = int(time.time())
    if current_time - timestamp > APPROVAL_LINK_TTL_SECONDS:
        return _html_page(
            "Yêu cầu nạp tiền thất bại: Link duyệt này đã hết hạn (quá 7 ngày)!",
            status_code=400,
        )

    # Verify signature over the exact values that were signed.
    expected_sig = sign_approval(user_id, package_id, timestamp)
    # Compare as bytes: compare_digest raises TypeError on non-ASCII str input.
    if not hmac.compare_digest(expected_sig.encode(), sig.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Mã phê duyệt không hợp lệ.")

    try:
        canonical_user_id = str(uuid.UUID(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="user_id không hợp lệ.") from exc

    # Idempotency key. Same format as the legacy "Ref: INV_..." description
    # marker (backfilled into credit_transactions.reference by migration 015).
    unique_marker = f"INV_{canonical_user_id}_{package_id}_{timestamp}"

    # Dedup check + balance update + ledger insert run in ONE transaction
    # inside add_credits (user row lock + unique index on reference), so a
    # double click can never credit twice.
    package = PACKAGES[package_id]
    try:
        new_balance = await add_credits(
            user_id=canonical_user_id,
            amount=package["credits"],
            tx_type="purchase",
            description=f"Duyệt nạp tiền thủ công. Gói {package['name']} nạp {package['credits']} credits. Ref: {unique_marker}",
            reference=unique_marker,
        )
    except DuplicateCreditReferenceError:
        return _html_page(
            "Giao dịch này đã được duyệt trước đó! Không thể duyệt lại.",
            status_code=200,
        )
    except HTTPException as exc:
        if exc.status_code == 404:
            return _html_page("Không tìm thấy người dùng.", status_code=404)
        raise
    except Exception:
        logger.exception(
            "Error processing manual credit addition for user %s", canonical_user_id
        )
        return _html_page("Lỗi hệ thống khi cập nhật số dư.", status_code=500)

    logger.info(
        "Manually approved %s credits for user %s. New balance: %s",
        package["credits"],
        canonical_user_id,
        new_balance,
    )
    safe_user_id = html.escape(canonical_user_id)
    safe_credits = html.escape(str(package["credits"]))
    safe_balance = html.escape(str(new_balance))
    return HTMLResponse(
        content=f"""
            <html>
                <head><title>Duyệt thành công</title></head>
                <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h1 style="color: #10B981;">Duyệt nạp tiền thành công!</h1>
                    <p>Tài khoản <b>{safe_user_id}</b> đã được cộng <b>{safe_credits} credits</b>.</p>
                    <p>Số dư hiện tại: <b>{safe_balance} credits</b>.</p>
                </body>
            </html>
            """,
    )
