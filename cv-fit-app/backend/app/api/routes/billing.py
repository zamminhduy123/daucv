import hashlib
import hmac
import logging
import os
import time
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

try:
    from app.dependencies import add_credits, get_current_user
except ImportError:

    async def add_credits(user_id, amount, tx_type, description):
        logger.info(f"MOCK add_credits for user {user_id}: added {amount} credits")
        return 9999

    async def get_current_user():
        return {
            "id": "12345678-1234-1234-1234-123456789012",
            "email": "test@example.com",
            "name": "Test User",
            "image": None,
            "credits": 10,
        }


try:
    from app.core.config import ALLOW_MOCK_BILLING, NEXTAUTH_SECRET
except (ImportError, AttributeError):
    ALLOW_MOCK_BILLING = os.getenv("ALLOW_MOCK_BILLING", "true").lower() == "true"
    NEXTAUTH_SECRET = os.getenv(
        "NEXTAUTH_SECRET", "super-secret-nextauth-key-change-in-prod"
    )

try:
    from app.schemas.billing import (
        BuyCreditsRequest,
        BuyCreditsResponse,
        MockPaymentConfirmRequest,
        MockPaymentConfirmResponse,
    )
except ImportError:
    from pydantic import BaseModel

    class BuyCreditsRequest(BaseModel):
        package_id: str

    class BuyCreditsResponse(BaseModel):
        checkout_url: str

    class MockPaymentConfirmRequest(BaseModel):
        package_id: str
        amount: int
        credits_to_add: int

    class MockPaymentConfirmResponse(BaseModel):
        success: bool
        new_credits: int


PACKAGES = {
    "starter": {"credits": 10, "price": 15000, "name": "Starter Pack"},
    "mid": {"credits": 20, "price": 24000, "name": "Mid Pack"},
    "pro": {"credits": 50, "price": 35000, "name": "Pro Pack"},
}


@router.post("/buy-credits", response_model=BuyCreditsResponse)
async def buy_credits(req: BuyCreditsRequest, user: dict = Depends(get_current_user)):
    if not ALLOW_MOCK_BILLING:
        raise HTTPException(
            status_code=403,
            detail="Cổng thanh toán thử nghiệm không được bật ở môi trường này.",
        )

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
    req: MockPaymentConfirmRequest, user: dict = Depends(get_current_user)
):
    if not ALLOW_MOCK_BILLING:
        raise HTTPException(
            status_code=403,
            detail="Cổng thanh toán thử nghiệm không được bật ở môi trường này.",
        )

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
            f"User {user['email']} successfully purchased {package['credits']} credits. New balance: {new_balance}"
        )

        return MockPaymentConfirmResponse(success=True, new_credits=new_balance)
    except Exception as e:
        logger.error(f"Error executing credit addition for user {user['id']}: {e}")
        raise HTTPException(status_code=500, detail=f"Không thể cập nhật số dư: {e}")


# --- Manual Billing (VietQR & Telegram one-click approval) ------------------

try:
    from app.core.db import Database
except ImportError:

    class Database:
        pool = None

        @classmethod
        async def connect(cls):
            pass

        @classmethod
        async def fetch_one(cls, query: str, *args):
            logger.info(f"MOCK Database.fetch_one: {query}")
            return None

        @classmethod
        async def execute(cls, query: str, *args):
            logger.info(f"MOCK Database.execute: {query}")
            return None


@router.post("/test-request")
async def test_request(
    req: BuyCreditsRequest,
    user_id: str = "ad0b8d18-7803-415d-8d0e-c41934b334bb",
    email: str = "ntminhduy123@gmail.com",
    name: str = "Duy Nguyen (D)",
):
    if not ALLOW_MOCK_BILLING:
        raise HTTPException(
            status_code=403,
            detail="Cổng thanh toán thử nghiệm không được bật ở môi trường này.",
        )
    mock_user = {
        "id": user_id,
        "email": email,
        "name": name,
        "image": None,
        "credits": 10,
    }
    return await request_manual_payment(req, user=mock_user)


@router.post("/request-manual-payment")
async def request_manual_payment(
    req: BuyCreditsRequest, user: dict = Depends(get_current_user)
):
    package_id = req.package_id
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Gói credit không hợp lệ.")

    package = PACKAGES[package_id]
    timestamp = int(time.time())

    # Generate a secure HMAC signature for the approval link using the shared secret
    message = f"{user['id']}:{package_id}:{timestamp}"
    sig = hmac.new(
        NEXTAUTH_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # Construct approval URL
    base_url = os.getenv("BASE_URL", "https://daucv.com")
    approve_url = (
        f"{base_url}/api/billing/approve-manual-payment"
        f"?user_id={user['id']}&package_id={package_id}&timestamp={timestamp}&sig={sig}"
    )

    # Format Telegram Message
    message_text = (
        f"🔔 <b>Yêu cầu nạp tiền mới!</b>\n\n"
        f"• <b>User:</b> {user['email']} (ID: <code>{user['id']}</code>)\n"
        f"• <b>Gói:</b> {package['name']} ({package['credits']} credits)\n"
        f"• <b>Số tiền:</b> {package['price']:,} VND\n"
        f"• <b>Nội dung chuyển khoản:</b> <code>DAUCV {package_id.upper()} {user['email']}</code>\n\n"
        f"👉 <a href='{approve_url}'>Duyệt nạp tiền (Approve)</a>"
    )

    # Send to Telegram if configured
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    sent_to_telegram = False

    if telegram_token and chat_id:
        try:
            import httpx

            # Async client or standard post with short timeout to prevent blocking
            with httpx.Client() as client:
                response = client.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message_text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=5.0,
                )
                if response.status_code == 200:
                    sent_to_telegram = True
                else:
                    logger.error(f"Telegram API responded with error: {response.text}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    if not sent_to_telegram:
        logger.info(
            f"\n================ TELEGRAM MOCK ALERTS ================\n"
            f"{message_text}\n"
            f"======================================================"
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
    user_id: str, package_id: str, timestamp: int, sig: str
):
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Gói credit không hợp lệ.")

    # Replay Protection: Link expires after 7 days (604800 seconds)
    current_time = int(time.time())
    if current_time - timestamp > 604800:
        return HTMLResponse(
            content="<h2>Yêu cầu nạp tiền thất bại: Link duyệt này đã hết hạn (quá 7 ngày)!</h2>",
            status_code=400,
        )

    # Verify signature
    message = f"{user_id}:{package_id}:{timestamp}"
    expected_sig = hmac.new(
        NEXTAUTH_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, sig):
        raise HTTPException(status_code=403, detail="Mã phê duyệt không hợp lệ.")

    # Deduplication check
    unique_marker = f"INV_{user_id}_{package_id}_{timestamp}"
    if not Database.pool:
        await Database.connect()

    existing_tx = await Database.fetch_one(
        "SELECT 1 FROM public.credit_transactions WHERE description LIKE $1",
        f"%{unique_marker}%",
    )
    if existing_tx:
        return HTMLResponse(
            content="<h2>Giao dịch này đã được duyệt trước đó! Không thể duyệt lại.</h2>",
            status_code=200,
        )

    # Top-Up credits using add_credits helper
    package = PACKAGES[package_id]
    try:
        new_balance = await add_credits(
            user_id=user_id,
            amount=package["credits"],
            tx_type="purchase",
            description=f"Duyệt nạp tiền thủ công. Gói {package['name']} nạp {package['credits']} credits. Ref: {unique_marker}",
        )
        logger.info(
            f"Manually approved {package['credits']} credits for user {user_id}. New balance: {new_balance}"
        )
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Duyệt thành công</title></head>
                <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h1 style="color: #10B981;">Duyệt nạp tiền thành công!</h1>
                    <p>Tài khoản <b>{user_id}</b> đã được cộng <b>{package["credits"]} credits</b>.</p>
                    <p>Số dư hiện tại: <b>{new_balance} credits</b>.</p>
                </body>
            </html>
            """
        )
    except Exception as e:
        logger.error(f"Error processing manual credit addition: {e}")
        return HTMLResponse(
            content=f"<h2>Lỗi hệ thống khi cập nhật số dư: {e}</h2>",
            status_code=500,
        )


@router.get("/debug-imports")
async def debug_imports():
    try:
        import inspect

        import app.dependencies

        return {
            "status": "ok",
            "message": "Import app.dependencies succeeded!",
            "file_path": inspect.getfile(app.dependencies),
            "has_add_credits": hasattr(app.dependencies, "add_credits"),
        }
    except Exception as e:
        import traceback

        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }


@router.get("/debug-db")
async def debug_db():
    try:
        from urllib.parse import urlparse

        from app.core.config import DATABASE_URL
        from app.core.db import Database

        parsed = urlparse(DATABASE_URL)
        db_info = {
            "host": parsed.hostname,
            "port": parsed.port,
        }

        if not Database.pool:
            await Database.connect()
        # Test query
        res = await Database.fetch_one("SELECT 1")
        return {
            "status": "ok",
            "message": "Database connection succeeded!",
            "db_info": db_info,
            "result": dict(res) if res else None,
        }
    except Exception as e:
        import traceback
        from urllib.parse import urlparse

        from app.core.config import DATABASE_URL

        parsed = urlparse(DATABASE_URL)
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
            "db_info": {
                "host": parsed.hostname,
                "port": parsed.port,
            },
            "traceback": traceback.format_exc(),
        }
