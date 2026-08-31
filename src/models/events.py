"""Razorpay Webhook event payload schemas and types."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RazorpayEventType(str, Enum):
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_AUTHORIZED = "payment.authorized"
    PAYMENT_CAPTURED = "payment.captured"
    REFUND_CREATED = "refund.created"
    DISPUTE_CREATED = "payment.dispute.created"
    DOWNTIME_STARTED = "payment.downtime.started"
    DOWNTIME_UPDATED = "payment.downtime.updated"
    DOWNTIME_RESOLVED = "payment.downtime.resolved"


class PaymentEntity(BaseModel):
    id: str = Field(description="Razorpay Payment ID e.g. pay_GXYZ123")
    order_id: str = Field(description="Razorpay Order ID e.g. order_GXYZ123")
    amount: int = Field(description="Amount in paise e.g. 450000 = ₹4500.00")
    currency: str = Field(default="INR")
    status: str = Field(description="Payment status: failed, captured, refunded, etc.")
    method: str = Field(default="card", description="Payment method: card, upi, netbanking, etc.")
    error_code: Optional[str] = Field(default=None, description="Decline/Error Code")
    error_description: Optional[str] = Field(default=None, description="Decline message")
    error_source: Optional[str] = Field(default=None, description="gateway, bank, customer, etc.")
    error_step: Optional[str] = Field(default=None, description="payment_authorization, etc.")
    error_reason: Optional[str] = Field(default=None, description="failure classification reason")
    email: Optional[str] = None
    contact: Optional[str] = None
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))


class DowntimeEntity(BaseModel):
    id: str = Field(description="Downtime ID e.g. down_123")
    method: str = Field(description="Affected method: upi, card, netbanking")
    bank: Optional[str] = Field(default=None, description="Bank code e.g. HDFC, ICIC")
    network: Optional[str] = Field(default=None, description="Card network e.g. VISA, MC")
    status: str = Field(description="started, resolved, updated")
    severity: str = Field(default="HIGH", description="HIGH, MEDIUM, LOW")
    begin: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    end: Optional[int] = None


class WebhookPayloadContainer(BaseModel):
    payment: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    refund: Optional[Dict[str, Any]] = None
    dispute: Optional[Dict[str, Any]] = None
    downtime: Optional[Dict[str, Any]] = None


class RazorpayWebhookEvent(BaseModel):
    """Authoritative incoming webhook structure from Razorpay."""
    
    entity: str = Field(default="event")
    account_id: str = Field(default="acc_default_merchant")
    event: RazorpayEventType
    contains: List[str] = Field(default_factory=list)
    payload: WebhookPayloadContainer
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
