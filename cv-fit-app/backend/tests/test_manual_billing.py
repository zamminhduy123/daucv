import hmac
import hashlib
import time
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# We use the HS256 secret configured in conftest or tests to calculate valid signatures
TEST_SECRET_KEY = "daucv"

def calculate_approval_sig(user_id: str, package_id: str, timestamp: int) -> str:
    message = f"{user_id}:{package_id}:{timestamp}"
    return hmac.new(
        TEST_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

import httpx

def test_request_manual_payment_success(client: TestClient) -> None:
    original_post = httpx.Client.post

    def mock_post_side_effect(self, url, *args, **kwargs):
        if "telegram.org" in str(url):
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {"ok": True}
            return mock_res
        return original_post(self, url, *args, **kwargs)

    with patch("httpx.Client.post", autospec=True, side_effect=mock_post_side_effect):
        # Request pro pack (50,000 VND)
        resp = client.post("/api/billing/request-manual-payment", json={"package_id": "pro"})
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["amount"] == 50000
    assert "qr_url" in data
    assert "bank_account" in data
    assert "TCB" in data["qr_url"] # Default bank is Techcombank (TCB)
    assert "PRO" in data["description"]

def test_request_manual_payment_invalid_package(client: TestClient) -> None:
    resp = client.post("/api/billing/request-manual-payment", json={"package_id": "invalid_package"})
    assert resp.status_code == 400
    assert "Gói credit không hợp lệ" in resp.json()["detail"]

@patch("app.api.routes.billing.add_credits", new_callable=AsyncMock)
@patch("app.core.db.Database.fetch_one", new_callable=AsyncMock)
def test_approve_manual_payment_success(mock_fetch_one: AsyncMock, mock_add_credits: AsyncMock, client: TestClient) -> None:
    mock_fetch_one.return_value = None # No existing transactions
    mock_add_credits.return_value = 60 # New balance

    user_id = "12345678-1234-1234-1234-123456789012"
    package_id = "pro"
    now_timestamp = int(time.time())
    sig = calculate_approval_sig(user_id, package_id, now_timestamp)

    resp = client.get(
        f"/api/billing/approve-manual-payment"
        f"?user_id={user_id}&package_id={package_id}&timestamp={now_timestamp}&sig={sig}"
    )

    assert resp.status_code == 200
    assert "Duyệt nạp tiền thành công" in resp.text
    assert "60 credits" in resp.text

    # Verify add_credits was triggered transactionally
    mock_add_credits.assert_called_once_with(
        user_id=user_id,
        amount=50, # Pro package credits = 50
        tx_type="purchase",
        description=f"Duyệt nạp tiền thủ công. Gói Pro Pack nạp 50 credits. Ref: INV_{user_id}_pro_{now_timestamp}"
    )

def test_approve_manual_payment_invalid_sig(client: TestClient) -> None:
    user_id = "12345678-1234-1234-1234-123456789012"
    package_id = "pro"
    now_timestamp = int(time.time())

    resp = client.get(
        f"/api/billing/approve-manual-payment"
        f"?user_id={user_id}&package_id={package_id}&timestamp={now_timestamp}&sig=invalid_sig_value"
    )

    assert resp.status_code == 403
    assert "Mã phê duyệt không hợp lệ" in resp.json()["detail"]

def test_approve_manual_payment_expired(client: TestClient) -> None:
    user_id = "12345678-1234-1234-1234-123456789012"
    package_id = "pro"
    # 8 days ago (expired, replay protection limit is 7 days)
    old_timestamp = int(time.time()) - (8 * 24 * 3600)
    sig = calculate_approval_sig(user_id, package_id, old_timestamp)

    resp = client.get(
        f"/api/billing/approve-manual-payment"
        f"?user_id={user_id}&package_id={package_id}&timestamp={old_timestamp}&sig={sig}"
    )

    assert resp.status_code == 400
    assert "Link duyệt này đã hết hạn" in resp.text

@patch("app.api.routes.billing.add_credits", new_callable=AsyncMock)
@patch("app.core.db.Database.fetch_one", new_callable=AsyncMock)
def test_approve_manual_payment_duplicate(mock_fetch_one: AsyncMock, mock_add_credits: AsyncMock, client: TestClient) -> None:
    # Mock that transaction ALREADY exists in public.credit_transactions
    mock_fetch_one.return_value = {"id": "already-exists"}

    user_id = "12345678-1234-1234-1234-123456789012"
    package_id = "pro"
    now_timestamp = int(time.time())
    sig = calculate_approval_sig(user_id, package_id, now_timestamp)

    resp = client.get(
        f"/api/billing/approve-manual-payment"
        f"?user_id={user_id}&package_id={package_id}&timestamp={now_timestamp}&sig={sig}"
    )

    assert resp.status_code == 200
    assert "Giao dịch này đã được duyệt trước đó" in resp.text
    mock_add_credits.assert_not_called()
