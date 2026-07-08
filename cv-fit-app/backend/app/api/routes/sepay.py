import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import APIRouter, HTTPException, Request

try:
    from app.dependencies import add_credits
except ImportError:
    async def add_credits(user_id, amount, tx_type, description):
        logger.info(f"MOCK add_credits for user {user_id}: added {amount} credits")
        return 9999

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

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sepay"])

# Retrieve SePay Webhook Secret Key from environment, fall back to sandbox key for testing
SEPAY_SECRET_KEY = os.getenv("SEPAY_SECRET_KEY", "sandbox-secret-key-change-in-prod")

PACKAGES = {
    "starter": {"credits": 10, "price": 20000, "name": "Starter Pack"},
    "pro": {"credits": 50, "price": 50000, "name": "Pro Pack"},
    "premium": {"credits": 120, "price": 100000, "name": "Premium Pack"},
}


def parse_invoice_number(invoice: str) -> dict | None:
    """
    Parse invoice number of format: INV_{user_id}_{package_id}_{timestamp}
    Returns a dictionary with user_id and package_id if valid, otherwise None.
    """
    if not invoice or not invoice.startswith("INV_"):
        return None

    parts = invoice.split("_")
    if len(parts) < 4:
        return None

    # Format: INV_<user_id>_<package_id>_<timestamp>
    user_id = parts[1]
    package_id = parts[2]
    return {"user_id": user_id, "package_id": package_id}


@router.post("/sepay/ipn")
async def sepay_ipn(request: Request):
    """
    SePay Webhook IPN Endpoint.
    Validates HMAC-SHA256 signature, parses transaction data, verifies amount,
    prevents double-crediting, and adds credits to user.
    """
    # 1. Retrieve headers
    signature_header = request.headers.get("x-sepay-signature") or request.headers.get(
        "X-SePay-Signature"
    )
    timestamp_header = request.headers.get("x-sepay-timestamp") or request.headers.get(
        "X-SePay-Timestamp"
    )

    if not signature_header or not timestamp_header:
        logger.warning("SePay IPN missing signature or timestamp headers")
        raise HTTPException(
            status_code=400, detail="Missing signature or timestamp headers"
        )

    # Normalize signature (remove 'sha256=' prefix if present)
    if signature_header.startswith("sha256="):
        signature_header = signature_header[len("sha256=") :]

    # 2. Replay Protection: check timestamp drift (5 minutes / 300 seconds)
    try:
        ts = int(timestamp_header)
    except ValueError:
        logger.warning(f"SePay IPN invalid timestamp format: {timestamp_header}")
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    current_time = int(time.time())
    if abs(current_time - ts) > 300:
        logger.warning(
            f"SePay IPN replay attack suspected. Timestamp drift: {abs(current_time - ts)}s"
        )
        raise HTTPException(
            status_code=400, detail="Request timestamp is too old or drift too large"
        )

    # 3. Read Raw Request Body
    raw_body = await request.body()
    raw_body_str = raw_body.decode("utf-8")

    # 4. Verify Signature
    # Signing string format: {timestamp}.{raw_body}
    signing_string = f"{timestamp_header}.{raw_body_str}"
    computed_sig = hmac.new(
        SEPAY_SECRET_KEY.encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_sig, signature_header):
        logger.warning("SePay IPN signature mismatch")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 5. Parse Payload JSON
    try:
        payload = json.loads(raw_body_str)
    except json.JSONDecodeError:
        logger.warning("SePay IPN payload is not valid JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 6. Extract fields (supports both Payment Gateway and Bank Transfer formats)
    invoice_number = None
    amount = 0
    sepay_tx_id = payload.get("id")

    if "order" in payload and isinstance(payload["order"], dict):
        # Gateway format
        invoice_number = payload["order"].get("order_invoice_number")
        amount_raw = payload["order"].get("order_amount", 0)
    else:
        # Bank transfer webhook format
        invoice_number = payload.get("code")
        amount_raw = payload.get("transferAmount", 0)

    try:
        amount = int(float(amount_raw))
    except (ValueError, TypeError):
        amount = 0

    if not invoice_number:
        logger.warning("SePay IPN payload missing invoice number / code")
        raise HTTPException(
            status_code=400, detail="Missing invoice number or payment code"
        )

    # 7. Parse invoice number to extract user_id & package_id
    parsed = parse_invoice_number(invoice_number)
    if not parsed:
        logger.warning(
            f"SePay IPN ignored: invalid invoice number format: {invoice_number}"
        )
        return {"success": True, "message": "Ignored invalid invoice format"}

    user_id = parsed["user_id"]
    package_id = parsed["package_id"]

    if package_id not in PACKAGES:
        logger.warning(f"SePay IPN ignored: invalid package: {package_id}")
        return {"success": True, "message": "Ignored invalid package"}

    package = PACKAGES[package_id]

    # 8. Validate amount matches package price
    if amount < package["price"]:
        logger.warning(
            f"SePay IPN payment amount {amount} is less than package price {package['price']} for package {package_id}"
        )
        return {"success": True, "message": "Ignored insufficient amount"}

    # 9. Deduplication check using description column in credit_transactions
    unique_tx_marker = f"Invoice: {invoice_number} | SePay ID: {sepay_tx_id}"

    if not Database.pool:
        await Database.connect()

    existing_tx = await Database.fetch_one(
        "SELECT 1 FROM public.credit_transactions WHERE description LIKE $1",
        f"%{unique_tx_marker}%",
    )
    if existing_tx:
        logger.info(f"SePay IPN: Transaction already processed for: {unique_tx_marker}")
        return {"success": True, "message": "Transaction already processed"}

    # 10. Allocate credits using database transaction
    try:
        new_balance = await add_credits(
            user_id=user_id,
            amount=package["credits"],
            tx_type="purchase",
            description=f"SePay Payment. Gói {package['name']} nạp {package['credits']} credits. {unique_tx_marker}",
        )
        logger.info(
            f"Successfully processed SePay payment for user {user_id}. Added {package['credits']} credits. New balance: {new_balance}"
        )
        return {"success": True, "new_balance": new_balance}
    except Exception as e:
        logger.error(f"Error processing SePay payment for user {user_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal database error updating credits: {e}"
        )
