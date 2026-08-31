"""Pytest fixtures and test helper utilities."""

import hashlib
import hmac
import json
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.api.app import create_app
from src.config import settings
from src.core.audit import audit_ledger
from src.core.downtime import rail_sentinel
from src.core.idempotency import idempotency_manager
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry


def generate_razorpay_signature(raw_body: bytes, secret: str = None) -> str:
    """Computes a valid HMAC-SHA256 signature for test payloads."""
    sec = secret or settings.razorpay_webhook_secret
    return hmac.new(
        key=sec.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()


@pytest_asyncio.fixture(autouse=True)
async def reset_runtime_state():
    """Resets all in-memory registries, idempotency locks, audit log, and telemetry before each test."""
    await state_machine.reset()
    await idempotency_manager.reset()
    await audit_ledger.reset()
    await telemetry.reset()
    await rail_sentinel.reset()
    settings.global_kill_switch = False
    yield


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP test client for FastAPI application."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def make_failed_payment_payload():
    def _maker(payment_id: str = "pay_test_001", order_id: str = "order_test_001", amount: int = 450000, error_code: str = "BAD_REQUEST_PAYMENT_TIMED_OUT"):
        return {
            "entity": "event",
            "account_id": "acc_merch_01",
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "amount": amount,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": error_code,
                        "error_description": "Bank network response timed out",
                        "error_source": "bank",
                        "error_step": "payment_authorization",
                        "email": "customer@example.com",
                        "contact": "+919876543210"
                    }
                }
            }
        }
    return _maker


@pytest.fixture
def make_captured_payment_payload():
    def _maker(payment_id: str = "pay_test_001", order_id: str = "order_test_001", amount: int = 450000):
        return {
            "entity": "event",
            "account_id": "acc_merch_01",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "amount": amount,
                        "currency": "INR",
                        "status": "captured",
                        "method": "card"
                    }
                }
            }
        }
    return _maker
