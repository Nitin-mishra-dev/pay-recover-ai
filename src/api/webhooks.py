"""FastAPI Webhook Ingestion Router with constant-time HMAC signature verification."""

import hashlib
import hmac
import json
from typing import Any, Dict
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from src.config import settings
from src.core.audit import AuditEventType, audit_ledger
from src.core.idempotency import idempotency_manager
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.models.events import RazorpayWebhookEvent


router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


def verify_razorpay_hmac_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verifies HMAC-SHA256 signature using constant-time string comparison."""
    if not signature or not secret:
        return False
    computed_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str = Header(None, alias="x-razorpay-event-id")
) -> Dict[str, Any]:
    """Ingests raw Razorpay webhook payloads with raw-body signature verification and event deduplication."""
    
    # 1. Extract RAW BYTES before any JSON parsing
    raw_body: bytes = await request.body()
    
    # 2. Verify HMAC-SHA256 signature
    if not x_razorpay_signature or not verify_razorpay_hmac_signature(
        raw_body=raw_body,
        signature=x_razorpay_signature,
        secret=settings.razorpay_webhook_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Razorpay-Signature header."
        )
    
    # 3. Deduplicate via x-razorpay-event-id
    event_id = x_razorpay_event_id or f"evt_synth_{hashlib.sha256(raw_body).hexdigest()[:16]}"
    is_new_event = await idempotency_manager.try_acquire_event(event_id)
    
    if not is_new_event:
        await telemetry.increment("duplicate_event_count")
        await audit_ledger.record_event(
            AuditEventType.WEBHOOK_DUPLICATE_IGNORED,
            {"event_id": event_id, "note": "duplicate_webhook_delivery_ignored"}
        )
        return {
            "status": "duplicate_ignored",
            "event_id": event_id,
            "message": "Event already ingested; duplicate execution prevented."
        }
    
    # 4. Parse verified JSON payload into domain model
    try:
        payload_dict = json.loads(raw_body.decode("utf-8"))
        webhook_event = RazorpayWebhookEvent.model_validate(payload_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed webhook JSON body: {str(e)}"
        )
    
    # 5. Process through Authoritative State Machine
    result = await state_machine.process_webhook_event(webhook_event)
    
    return {
        "status": "processed",
        "event_id": event_id,
        "event_type": webhook_event.event.value,
        "detail": result
    }
