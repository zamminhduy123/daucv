import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

# The default fallback key used in sepay.py for testing
TEST_SECRET_KEY = "sandbox-secret-key-change-in-prod"


def calculate_sig(timestamp: str, body_str: str) -> str:
    signing_string = f"{timestamp}.{body_str}"
    return hmac.new(
        TEST_SECRET_KEY.encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def test_sepay_ipn_missing_headers(client: TestClient) -> None:
    resp = client.post("/sepay/ipn", json={})
    assert resp.status_code == 400
    assert "Missing signature" in resp.json()["detail"]


def test_sepay_ipn_invalid_timestamp(client: TestClient) -> None:
    headers = {"X-SePay-Signature": "some-sig", "X-SePay-Timestamp": "not-a-number"}
    resp = client.post("/sepay/ipn", json={}, headers=headers)
    assert resp.status_code == 400
    assert "Invalid timestamp" in resp.json()["detail"]


def test_sepay_ipn_replay_attack(client: TestClient) -> None:
    # 10 minutes ago
    old_timestamp = str(int(time.time()) - 600)
    body = {"id": 123}
    body_str = json.dumps(body)
    sig = calculate_sig(old_timestamp, body_str)

    headers = {"X-SePay-Signature": sig, "X-SePay-Timestamp": old_timestamp}
    resp = client.post("/sepay/ipn", content=body_str, headers=headers)
    assert resp.status_code == 400
    assert "timestamp is too old" in resp.json()["detail"]


def test_sepay_ipn_invalid_signature(client: TestClient) -> None:
    now_timestamp = str(int(time.time()))
    body = {"id": 123}
    body_str = json.dumps(body)

    headers = {
        "X-SePay-Signature": "invalid-sig-here",
        "X-SePay-Timestamp": now_timestamp,
    }
    resp = client.post("/sepay/ipn", content=body_str, headers=headers)
    assert resp.status_code == 400
    assert "Invalid signature" in resp.json()["detail"]


@patch("app.api.routes.sepay.add_credits", new_callable=AsyncMock)
@patch("app.core.db.Database.fetch_one", new_callable=AsyncMock)
def test_sepay_ipn_gateway_success(
    mock_fetch_one: AsyncMock, mock_add_credits: AsyncMock, client: TestClient
) -> None:
    # Set DB mock: no existing transactions
    mock_fetch_one.return_value = None
    mock_add_credits.return_value = 20  # returns new balance

    now_timestamp = str(int(time.time()))
    user_id = "12345678-1234-1234-1234-123456789012"
    invoice = f"INV_{user_id}_starter_{now_timestamp}"

    body = {
        "id": 92704,
        "notification_type": "ORDER_PAID",
        "order": {
            "id": "e2c195be-c721-47eb-b323-99ab24e52d85",
            "order_invoice_number": invoice,
            "order_amount": "20000.00",  # matches Starter price (20,000 VND)
        },
    }
    body_str = json.dumps(body)
    sig = calculate_sig(now_timestamp, body_str)

    headers = {"X-SePay-Signature": f"sha256={sig}", "X-SePay-Timestamp": now_timestamp}

    resp = client.post("/sepay/ipn", content=body_str, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["new_balance"] == 20

    # Verify mock_add_credits was called with correct args
    mock_add_credits.assert_called_once_with(
        user_id=user_id,
        amount=10,  # Starter package credits is 10
        tx_type="purchase",
        description=f"SePay Payment. Gói Starter Pack nạp 10 credits. Invoice: {invoice} | SePay ID: 92704",
    )


@patch("app.api.routes.sepay.add_credits", new_callable=AsyncMock)
@patch("app.core.db.Database.fetch_one", new_callable=AsyncMock)
def test_sepay_ipn_bank_transfer_success(
    mock_fetch_one: AsyncMock, mock_add_credits: AsyncMock, client: TestClient
) -> None:
    mock_fetch_one.return_value = None
    mock_add_credits.return_value = 60  # returns new balance

    now_timestamp = str(int(time.time()))
    user_id = "12345678-1234-1234-1234-123456789012"
    invoice = f"INV_{user_id}_pro_{now_timestamp}"

    body = {
        "id": 11111,
        "gateway": "Techcombank",
        "code": invoice,
        "transferAmount": 50000,  # matches Pro price (50,000 VND)
    }
    body_str = json.dumps(body)
    sig = calculate_sig(now_timestamp, body_str)

    headers = {"X-SePay-Signature": sig, "X-SePay-Timestamp": now_timestamp}

    resp = client.post("/sepay/ipn", content=body_str, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["new_balance"] == 60

    # Verify mock_add_credits was called with correct args (Pro Pack = 50 credits)
    mock_add_credits.assert_called_once_with(
        user_id=user_id,
        amount=50,
        tx_type="purchase",
        description=f"SePay Payment. Gói Pro Pack nạp 50 credits. Invoice: {invoice} | SePay ID: 11111",
    )


@patch("app.api.routes.sepay.add_credits", new_callable=AsyncMock)
@patch("app.core.db.Database.fetch_one", new_callable=AsyncMock)
def test_sepay_ipn_duplicate_transaction(
    mock_fetch_one: AsyncMock, mock_add_credits: AsyncMock, client: TestClient
) -> None:
    # Set DB mock: transaction ALREADY exists
    mock_fetch_one.return_value = {"id": "some-id"}

    now_timestamp = str(int(time.time()))
    user_id = "12345678-1234-1234-1234-123456789012"
    invoice = f"INV_{user_id}_pro_{now_timestamp}"

    body = {"id": 22222, "code": invoice, "transferAmount": 50000}
    body_str = json.dumps(body)
    sig = calculate_sig(now_timestamp, body_str)

    headers = {"X-SePay-Signature": sig, "X-SePay-Timestamp": now_timestamp}

    resp = client.post("/sepay/ipn", content=body_str, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["message"] == "Transaction already processed"

    # Ensure credits were NOT added again
    mock_add_credits.assert_not_called()


@patch("app.api.routes.sepay.add_credits", new_callable=AsyncMock)
@patch("app.core.db.Database.fetch_one", new_callable=AsyncMock)
def test_sepay_ipn_insufficient_amount(
    mock_fetch_one: AsyncMock, mock_add_credits: AsyncMock, client: TestClient
) -> None:
    mock_fetch_one.return_value = None

    now_timestamp = str(int(time.time()))
    user_id = "12345678-1234-1234-1234-123456789012"
    invoice = f"INV_{user_id}_premium_{now_timestamp}"

    body = {
        "id": 33333,
        "code": invoice,
        "transferAmount": 10000,  # Premium is 100,000 VND, paying 10,000 is insufficient
    }
    body_str = json.dumps(body)
    sig = calculate_sig(now_timestamp, body_str)

    headers = {"X-SePay-Signature": sig, "X-SePay-Timestamp": now_timestamp}

    resp = client.post("/sepay/ipn", content=body_str, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["message"] == "Ignored insufficient amount"

    # Ensure credits were NOT added
    mock_add_credits.assert_not_called()
