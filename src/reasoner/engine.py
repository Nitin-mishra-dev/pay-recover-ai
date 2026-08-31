"""Combined Selective Contextual Reasoner Engine (System B)."""

import time
from typing import Any, List, Optional, Tuple
from eval.baselines import BaseRecoveryPolicy, PayRecoverAIEngine
from eval.schemas import ObservableCase, PolicyDecision
from src.config import settings
from src.core.economics import HARD_DECLINE_CODES
from src.models.actions import (
    ActionType,
    EscalateParameters,
    NoActionParameters,
    NotifyParameters,
    RetryParameters,
)
from src.reasoner.client import ContextualLLMClient, llm_reasoner_client
from src.reasoner.router import AmbiguityClassifier, ambiguity_router
from src.reasoner.schemas import ReasonerInvocationResult


class SelectiveLLMPayRecoverEngine(BaseRecoveryPolicy):
    """System B: Deterministic Engine with Selective LLM Diagnosis on Ambiguous Cases."""
    
    def __init__(
        self,
        llm_client: Optional[ContextualLLMClient] = None,
        router: Optional[AmbiguityClassifier] = None,
        deterministic_fallback: Optional[PayRecoverAIEngine] = None
    ):
        self.llm_client = llm_client or llm_reasoner_client
        self.router = router or ambiguity_router
        self.fallback_engine = deterministic_fallback or PayRecoverAIEngine()
        self.total_evaluated: int = 0
        self.total_llm_invocations: int = 0
        self.total_llm_cost_inr: float = 0.0
        self.total_llm_latency_ms: float = 0.0
        self.total_fallbacks: int = 0
    
    @property
    def name(self) -> str:
        return "System B: Selective LLM Reasoner"
    
    @property
    def description(self) -> str:
        return "Hybrid architecture routing ambiguous/conflicting/high-value cases to structured LLM diagnosis."
    
    def decide(self, case: ObservableCase, latent: Any = None, **kwargs) -> PolicyDecision:
        self.total_evaluated += 1
        
        # 1. Ambiguity Router Gate
        needs_llm, route_reason = self.router.should_route_to_llm(case)
        
        # Fast Path: bypass LLM
        if not needs_llm:
            return self.fallback_engine.decide(case)
        
        # Slow Path: Invoke Contextual LLM
        self.total_llm_invocations += 1
        llm_res: ReasonerInvocationResult = self.llm_client.diagnose(case)
        self.total_llm_cost_inr += llm_res.estimated_cost_inr
        self.total_llm_latency_ms += llm_res.latency_ms
        
        # Fallback on LLM failure or malformed schema
        if llm_res.fallback_used or not llm_res.candidates:
            self.total_fallbacks += 1
            dec = self.fallback_engine.decide(case)
            dec.reason_codes.append(f"llm_fallback_{llm_res.validation_error or 'empty_candidates'}")
            return dec
        
        # 2. Score LLM-recommended candidate actions through Economic Engine
        amount_inr = case.payment.amount_inr
        p_natural = self.fallback_engine._estimate_natural_recovery(case)
        scored_candidates: List[PolicyDecision] = []
        
        for cand in llm_res.candidates:
            atype = cand.action_type
            p_rec = cand.estimated_recovery_prob
            p_inc = max(0.0, p_rec - p_natural)
            
            # Action cost lookup
            if atype == ActionType.NO_ACTION:
                cost = 0.0
            elif atype == ActionType.RETRY_PAYMENT:
                cost = settings.direct_retry_cost_inr
            elif atype == ActionType.NOTIFY_PAYMENT_LINK:
                ch = cand.parameters.get("channel", "SMS")
                cost = (settings.email_cost_inr if ch == "EMAIL" else settings.sms_cost_inr) + settings.customer_annoyance_penalty_inr
            elif atype == ActionType.ESCALATE_TO_SUPPORT:
                cost = settings.human_ops_cost_inr
            else:
                cost = 0.0
            
            iev = (p_inc * amount_inr) - cost
            
            scored_candidates.append(PolicyDecision(
                action_type=atype,
                action_parameters=cand.parameters,
                predicted_recovery_prob=round(p_rec, 4),
                predicted_natural_prob=round(p_natural, 4),
                predicted_iev_inr=round(iev, 2),
                confidence=llm_res.confidence,
                reason_codes=[f"llm_diagnosis_{llm_res.diagnosis.value}", f"route_{route_reason}"]
            ))
        
        # Fallback No-Action option
        scored_candidates.append(PolicyDecision(
            action_type=ActionType.NO_ACTION,
            action_parameters=NoActionParameters(reason="zero_iev_floor").model_dump(),
            predicted_recovery_prob=p_natural,
            predicted_natural_prob=p_natural,
            predicted_iev_inr=0.0,
            confidence=1.0,
            reason_codes=["zero_cost_baseline"]
        ))
        
        # Maximize IEV
        scored_candidates.sort(key=lambda c: c.predicted_iev_inr, reverse=True)
        best = scored_candidates[0]
        
        if best.predicted_iev_inr <= 0:
            for c in scored_candidates:
                if c.action_type == ActionType.NO_ACTION:
                    return c
        
        return best
    
    def get_telemetry(self) -> dict:
        coverage = (self.total_llm_invocations / max(1, self.total_evaluated)) * 100
        avg_lat = self.total_llm_latency_ms / max(1, self.total_llm_invocations)
        return {
            "total_evaluated": self.total_evaluated,
            "llm_invocations": self.total_llm_invocations,
            "ai_coverage_pct": round(coverage, 2),
            "total_llm_cost_inr": round(self.total_llm_cost_inr, 4),
            "avg_llm_latency_ms": round(avg_lat, 2),
            "fallback_count": self.total_fallbacks
        }
