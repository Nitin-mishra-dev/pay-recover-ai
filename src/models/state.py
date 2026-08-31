"""State machine entities, enums, and case tracking aggregates."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PaymentState(str, Enum):
    """Authoritative lifecycle states for payment cases."""
    
    OBSERVED_FAILED = "OBSERVED_FAILED"
    ANALYZING = "ANALYZING"
    DECISION_READY = "DECISION_READY"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    CAPTURED = "CAPTURED"
    STOPPED = "STOPPED"
    CANCELLED_STALE = "CANCELLED_STALE"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class ActionStatus(str, Enum):
    """Lifecycle status of an individual recovery intervention."""
    
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    AUTHORIZED = "AUTHORIZED"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED_STALE = "CANCELLED_STALE"
    BLOCKED_SAFETY = "BLOCKED_SAFETY"
    BLOCKED_KILL_SWITCH = "BLOCKED_KILL_SWITCH"


class RecoveryActionRecord(BaseModel):
    """Record of a proposed, scheduled, or executed recovery action."""
    
    action_id: str = Field(description="Unique UUID for this specific action instance")
    case_id: str
    payment_id: str
    order_id: str
    merchant_id: str = Field(default="merch_default")
    action_type: str
    action_parameters: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(description="Deterministic hash of action parameters & identity")
    status: ActionStatus = Field(default=ActionStatus.PROPOSED)
    scheduled_for: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    outcome: Optional[str] = None
    expected_incremental_value: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaymentCase(BaseModel):
    """Authoritative Aggregate for a failed payment undergoing recovery."""
    
    case_id: str = Field(description="Unique case identifier")
    payment_id: str
    order_id: str
    merchant_id: str = Field(default="merch_default")
    amount_paise: int
    currency: str = Field(default="INR")
    state: PaymentState = Field(default=PaymentState.OBSERVED_FAILED)
    payment_method: str = Field(default="card")
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    customer_email: Optional[str] = None
    customer_contact: Optional[str] = None
    attempt_count: int = Field(default=0)
    notification_count: int = Field(default=0)
    active_action_id: Optional[str] = None
    last_event_type: str = Field(default="payment.failed")
    last_attempt_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
