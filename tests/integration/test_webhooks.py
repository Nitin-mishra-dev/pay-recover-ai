"""Integration tests for FastAPI Webhook Ingestion with raw-body signature validation and deduplication."""

import json
import pytest
from tests.conftest import generate_razorpay_signature
from src.core.telemetry import telemetry


@pytest.mark.asyncio
async def test_webhook_signature_verification_success(async_client, make_failed_payment_payload):
    """Raw-body HMAC verification succeeds with correct secret."""
    payload_dict = make_failed_payment_payload(payment_id="pay_sig_01", order_id="order_sig_01")
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = generate_razorpay_signature(raw_bytes)
    
    response = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers={
            "X-Razorpay-Signature": signature,
            "x-razorpay-event-id": "evt_sig_01",
            "Content-Type": "application/json"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_id"] == "evt_sig_01"


@pytest.mark.asyncio
async def test_webhook_signature_verification_failure(async_client, make_failed_payment_payload):
    """Invalid signature returns HTTP 401 Unauthorized before parsing payload."""
    payload_dict = make_failed_payment_payload(payment_id="pay_bad_01")
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    
    response = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers={
            "X-Razorpay-Signature": "invalid_hex_signature_string",
            "x-razorpay-event-id": "evt_bad_01",
            "Content-Type": "application/json"
        }
    )
    assert response.status_code == 401
    assert "Invalid or missing X-Razorpay-Signature" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_duplicate_delivery_deduplication(async_client, make_failed_payment_payload):
    """TEST 2: Same webhook delivered 10 times -> 1 processed, 9 duplicate events, 0 duplicate executions."""
    payload_dict = make_failed_payment_payload(payment_id="pay_dedup_01", order_id="order_dedup_01")
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = generate_razorpay_signature(raw_bytes)
    event_id = "evt_dedup_repeat_10x"
    
    responses = []
    for i in range(10):
        res = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_bytes,
            headers={
                "X-Razorpay-Signature": signature,
                "x-razorpay-event-id": event_id,
                "Content-Type": "application/json"
            }
        )
        responses.append(res)
    
    # 1. Assert all returned HTTP 200
    for r in responses:
        assert r.status_code == 200
    
    # 2. First delivery was processed
    assert responses[0].json()["status"] == "processed"
    
    # 3. Subsequent 9 deliveries were recognized as duplicates and ignored
    for r in responses[1:]:
        assert r.json()["status"] == "duplicate_ignored"
        assert r.json()["event_id"] == event_id
    
    # 4. Telemetry asserts
    dup_events = await telemetry.get_counter("duplicate_event_count")
    dup_execs = await telemetry.get_counter("duplicate_execution_attempt_count")
    
    assert dup_events == 9
    assert dup_execs == 0
