"""Data schemas and type definitions for the independent evaluation harness."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.models.actions import ActionType


class LatencyBucket(str, Enum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    OUTAGE = "OUTAGE"


class CustomerContext(BaseModel):
    customer_id: str
    tenure_days: int = Field(ge=0)
    historical_attempts: int = Field(ge=0)
    historical_successes: int = Field(ge=0)
    historical_recovery_rate: float = Field(ge=0.0, le=1.0)
    avg_order_value_inr: float = Field(ge=0.0)
    preferred_method: str = Field(default="card")
    dnd_active: bool = Field(default=False)


class PaymentContext(BaseModel):
    payment_id: str
    order_id: str
    merchant_id: str = Field(default="merch_default")
    amount_paise: int = Field(gt=0)
    amount_inr: float = Field(gt=0.0)
    currency: str = Field(default="INR")
    method: str = Field(default="card")
    failure_code: str
    failure_description: str
    attempt_number: int = Field(default=1, ge=1)
    gateway: str = Field(default="HDFC")
    issuer_bank: str = Field(default="HDFC")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EnvironmentContext(BaseModel):
    rail_health_score: int = Field(ge=0, le=100, description="0 is total outage, 100 is pristine health")
    is_downtime_active: bool = Field(default=False)
    latency_bucket: LatencyBucket = Field(default=LatencyBucket.NORMAL)
    recent_rail_failure_rate: float = Field(ge=0.0, le=1.0)


class ObservableCase(BaseModel):
    """The ONLY context exposed to policies, agents, and baselines."""
    
    case_id: str
    payment: PaymentContext
    customer: CustomerContext
    environment: EnvironmentContext


class LatentGroundTruth(BaseModel):
    """SEALED hidden physics and counterfactual outcomes. Never exposed to policies."""
    
    latent_case_id: str
    is_fraud_true: bool = Field(default=False)
    is_card_permanently_dead: bool = Field(default=False)
    true_payer_intent_score: float = Field(ge=0.0, le=1.0)
    true_outage_duration_seconds: int = Field(ge=0)
    
    # Counterfactual realization table: maps action key -> binary outcome Y in {0, 1}
    # Key format: "action_type:delay_seconds" or "action_type:channel"
    counterfactual_outcomes: Dict[str, int] = Field(
        description="Hidden ground-truth outcomes for every possible intervention"
    )
    
    # True latent recovery probabilities under each intervention
    latent_probabilities: Dict[str, float] = Field(
        description="True underlying probabilities used by the hidden world sampler"
    )


class TransactionRecord(BaseModel):
    """A paired evaluation item containing public observables and sealed latent truth."""
    
    observable: ObservableCase
    latent: LatentGroundTruth


class PolicyDecision(BaseModel):
    """The decision output produced by an evaluated baseline or agent."""
    
    action_type: ActionType
    action_parameters: Dict[str, Any] = Field(default_factory=dict)
    predicted_recovery_prob: float = Field(ge=0.0, le=1.0)
    predicted_natural_prob: float = Field(ge=0.0, le=1.0)
    predicted_iev_inr: float
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    reason_codes: List[str] = Field(default_factory=list)


class RealizedOutcome(BaseModel):
    """Realized simulation result when a policy decision meets the hidden world."""
    
    case_id: str
    chosen_action: ActionType
    action_parameters: Dict[str, Any]
    captured: bool
    amount_inr: float
    recovered_revenue_inr: float
    natural_recovered_revenue_inr: float
    incremental_recovered_revenue_inr: float
    intervention_cost_inr: float
    risk_penalty_inr: float
    net_incremental_value_inr: float
    regret_inr: float
    safety_violation: bool = Field(default=False)
    safety_violation_reason: Optional[str] = None
    predicted_prob: float
    true_latent_prob: float
