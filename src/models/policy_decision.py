"""Pydantic model validating structured decision outputs from the reasoner."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.models.actions import ActionType


class PolicyDecisionPayload(BaseModel):
    """Structured decision object produced by LLM or deterministic reasoner."""
    
    decision_id: str = Field(description="UUID of the decision")
    case_id: str
    payment_id: str
    order_id: str
    action: ActionType
    action_parameters: Dict[str, Any] = Field(default_factory=dict)
    reason_codes: List[str] = Field(min_length=1)
    expected_recovery_amount: float = Field(ge=0.0)
    expected_cost: float = Field(ge=0.0)
    expected_net_incremental_value: float
    confidence: float = Field(ge=0.0, le=1.0)
    policy_version: str = Field(default="v1.0.0")
    model_version: str = Field(default="rule_scorer_v1")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
