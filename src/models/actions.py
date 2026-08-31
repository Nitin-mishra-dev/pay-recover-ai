"""Canonical recovery action contracts and parameters."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    RETRY_PAYMENT = "retry_payment"
    NOTIFY_PAYMENT_LINK = "notify_payment_link"
    ESCALATE_TO_SUPPORT = "escalate_to_support"
    NO_ACTION = "no_action"


class RetryParameters(BaseModel):
    delay_seconds: int = Field(default=0, ge=0, le=86400, description="Scheduled delay before executing re-attempt")
    attempt_number: int = Field(default=1, ge=1, le=5)
    route_hint: Optional[str] = Field(default=None, description="Optional gateway/rail routing suggestion")


class NotifyParameters(BaseModel):
    channel: str = Field(default="SMS", description="EMAIL or SMS")
    template_id: str = Field(default="payment_retry_link_v1")
    link_expiry_minutes: int = Field(default=1440, ge=5, le=10080)


class EscalateParameters(BaseModel):
    reason: str = Field(default="high_value_complex_failure")
    diagnostic_summary: Optional[str] = None


class NoActionParameters(BaseModel):
    reason: str = Field(default="hard_decline_or_negative_iev")


class CandidateAction(BaseModel):
    """An action evaluated and proposed for execution."""
    
    action_type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    predicted_recovery_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    natural_recovery_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    incremental_prob: float = Field(default=0.0)
    gross_expected_value_inr: float = Field(default=0.0)
    direct_cost_inr: float = Field(default=0.0)
    risk_penalty_inr: float = Field(default=0.0)
    expected_incremental_value_inr: float = Field(default=0.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
