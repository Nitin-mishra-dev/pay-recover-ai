"""Contract schemas for the Selective Contextual LLM Reasoner."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from src.models.actions import ActionType


class DiagnosisCategory(str, Enum):
    TRANSIENT_NETWORK_GLITCH = "transient_network_glitch"
    BANK_DEGRADATION = "bank_degradation"
    CUSTOMER_AUTHENTICATION_ACTIONABLE = "customer_authentication_actionable"
    INSUFFICIENT_FUNDS_TOPUP = "insufficient_funds_topup"
    HIGH_VALUE_AMBIGUOUS_POLICY = "high_value_ambiguous_policy"
    PERMANENT_HARD_DECLINE = "permanent_hard_decline"
    POTENTIAL_FRAUD_RISK = "potential_fraud_risk"
    UNKNOWN_AMBIGUITY = "unknown_ambiguity"


class LLMCandidateAction(BaseModel):
    action_type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    estimated_recovery_prob: float = Field(ge=0.0, le=1.0)


class LLMDiagnosisResponse(BaseModel):
    """Strict structured contract for LLM diagnostic outputs."""
    
    diagnosis: DiagnosisCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence score strictly in [0.0, 1.0]")
    evidence: List[str] = Field(min_length=1, description="List of factual contextual observations supporting the diagnosis")
    recommended_candidates: List[LLMCandidateAction] = Field(min_length=1, description="Ranked list of candidate interventions")
    
    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be strictly between 0.0 and 1.0")
        return round(v, 4)


class ReasonerInvocationResult(BaseModel):
    """Diagnostic execution container capturing latency, tokens, cost, and output."""
    
    used_llm: bool
    diagnosis: DiagnosisCategory
    confidence: float
    evidence: List[str]
    candidates: List[LLMCandidateAction]
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_inr: float = 0.0
    fallback_used: bool = False
    validation_error: Optional[str] = None
