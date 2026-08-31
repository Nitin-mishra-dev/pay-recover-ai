"""The Four Locked Baseline Strategies for Economic Benchmarking."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from eval.schemas import ObservableCase, PolicyDecision
from src.config import settings
from src.core.economics import HARD_DECLINE_CODES, SOFT_DECLINE_CODES
from src.models.actions import (
    ActionType,
    EscalateParameters,
    NoActionParameters,
    NotifyParameters,
    RetryParameters,
)


class BaseRecoveryPolicy(ABC):
    """Abstract interface for all evaluated recovery strategies."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    def decide(self, case: ObservableCase) -> PolicyDecision:
        """Evaluates observable context and selects a recovery action."""
        pass


class NoActionBaseline(BaseRecoveryPolicy):
    """Baseline 0: Passive Control Floor (Takes no action; zero cost)."""
    
    @property
    def name(self) -> str:
        return "Baseline 0: No Action"
    
    @property
    def description(self) -> str:
        return "Complete inaction upon failure. Realizes only natural customer reattempts."
    
    def decide(self, case: ObservableCase) -> PolicyDecision:
        return PolicyDecision(
            action_type=ActionType.NO_ACTION,
            action_parameters=NoActionParameters(reason="passive_baseline_control").model_dump(),
            predicted_recovery_prob=0.0,
            predicted_natural_prob=0.0,
            predicted_iev_inr=0.0,
            confidence=1.0,
            reason_codes=["passive_control_floor"]
        )


class BlindRetryBaseline(BaseRecoveryPolicy):
    """Baseline 1: Naïve Uniform Retry (Retries 100% of failures at fixed 5m delay)."""
    
    @property
    def name(self) -> str:
        return "Baseline 1: Blind Retry"
    
    @property
    def description(self) -> str:
        return "Blindly retries every failed transaction once after 300s, ignoring decline codes and rail outages."
    
    def decide(self, case: ObservableCase) -> PolicyDecision:
        return PolicyDecision(
            action_type=ActionType.RETRY_PAYMENT,
            action_parameters=RetryParameters(delay_seconds=300, attempt_number=1).model_dump(),
            predicted_recovery_prob=0.50,
            predicted_natural_prob=0.0,
            predicted_iev_inr=round((0.50 * case.payment.amount_inr) - 0.50, 2),
            confidence=0.5,
            reason_codes=["blind_uniform_retry"]
        )


class StaticRulesBaseline(BaseRecoveryPolicy):
    """Baseline 2: Industry Standard Static Dunning Rules."""
    
    @property
    def name(self) -> str:
        return "Baseline 2: Static Rules Engine"
    
    @property
    def description(self) -> str:
        return "Rule table based on error codes without degradation awareness or incremental value calculations."
    
    def decide(self, case: ObservableCase) -> PolicyDecision:
        amount_inr = case.payment.amount_inr
        code = case.payment.failure_code
        
        # 1. Hard Decline Rule
        if code in HARD_DECLINE_CODES:
            return PolicyDecision(
                action_type=ActionType.NO_ACTION,
                action_parameters=NoActionParameters(reason="static_rule_hard_decline").model_dump(),
                predicted_recovery_prob=0.0,
                predicted_natural_prob=0.0,
                predicted_iev_inr=0.0,
                confidence=0.9,
                reason_codes=["static_hard_decline_filter"]
            )
        
        # 2. High Value Rule
        if amount_inr >= 25000:
            return PolicyDecision(
                action_type=ActionType.ESCALATE_TO_SUPPORT,
                action_parameters=EscalateParameters(reason="static_high_value_rule").model_dump(),
                predicted_recovery_prob=0.60,
                predicted_natural_prob=0.05,
                predicted_iev_inr=round((0.55 * amount_inr) - 50.0, 2),
                confidence=0.8,
                reason_codes=["static_high_value_escalation"]
            )
        
        # 3. Customer Actionable Rule
        if code in ["BAD_REQUEST_INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED"]:
            return PolicyDecision(
                action_type=ActionType.NOTIFY_PAYMENT_LINK,
                action_parameters=NotifyParameters(channel="SMS").model_dump(),
                predicted_recovery_prob=0.40,
                predicted_natural_prob=0.08,
                predicted_iev_inr=round((0.32 * amount_inr) - 2.20, 2),
                confidence=0.7,
                reason_codes=["static_customer_action_sms"]
            )
        
        # 4. Soft Decline Gateway Error -> Fixed 300s Retry (ignoring rail degradation)
        return PolicyDecision(
            action_type=ActionType.RETRY_PAYMENT,
            action_parameters=RetryParameters(delay_seconds=300, attempt_number=1).model_dump(),
            predicted_recovery_prob=0.70,
            predicted_natural_prob=0.10,
            predicted_iev_inr=round((0.60 * amount_inr) - 0.50, 2),
            confidence=0.8,
            reason_codes=["static_soft_decline_retry"]
        )


class PayRecoverAIEngine(BaseRecoveryPolicy):
    """Baseline 3: PayRecover AI (Adaptive Causal Incremental Decision Engine)."""
    
    @property
    def name(self) -> str:
        return "Baseline 3: PayRecover AI"
    
    @property
    def description(self) -> str:
        return "Adaptive decision layer maximizing Net Incremental Value with degradation-aware timing."
    
    def _estimate_natural_recovery(self, case: ObservableCase) -> float:
        """Estimates organic baseline recovery probability."""
        if case.payment.failure_code in HARD_DECLINE_CODES:
            return 0.0
        amount = case.payment.amount_inr
        tenure_bonus = min(0.08, case.customer.tenure_days / 5000.0)
        if amount < 1000:
            return 0.15 + tenure_bonus
        elif amount < 10000:
            return 0.08 + tenure_bonus
        return 0.03 + tenure_bonus
    
    def decide(self, case: ObservableCase) -> PolicyDecision:
        amount_inr = case.payment.amount_inr
        code = case.payment.failure_code
        env = case.environment
        cust = case.customer
        
        # 1. Hard Decline Filter: Immediate No Action
        if code in HARD_DECLINE_CODES:
            return PolicyDecision(
                action_type=ActionType.NO_ACTION,
                action_parameters=NoActionParameters(reason="hard_decline_zero_recovery").model_dump(),
                predicted_recovery_prob=0.0,
                predicted_natural_prob=0.0,
                predicted_iev_inr=0.0,
                confidence=0.99,
                reason_codes=["hard_decline_safety_filter"]
            )
        
        p_natural = self._estimate_natural_recovery(case)
        candidates: List[PolicyDecision] = []
        
        # 2. Evaluate Smart Retry (Immediate vs Adaptive Delay based on Rail Health)
        is_degraded = env.is_downtime_active or (env.rail_health_score < 60)
        delay_chosen = 1800 if is_degraded else 300
        
        # Predicted probability adapts to rail health
        if is_degraded and delay_chosen < 1800:
            p_rec_retry = 0.15
        elif code in ["BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR", "BANK_TECHNICAL_ERROR"]:
            p_rec_retry = 0.85
        elif code in ["BAD_REQUEST_INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK"]:
            p_rec_retry = 0.25
        else:
            p_rec_retry = 0.40
        
        p_inc_retry = max(0.0, p_rec_retry - p_natural)
        iev_retry = (p_inc_retry * amount_inr) - settings.direct_retry_cost_inr
        
        candidates.append(PolicyDecision(
            action_type=ActionType.RETRY_PAYMENT,
            action_parameters=RetryParameters(delay_seconds=delay_chosen, attempt_number=1).model_dump(),
            predicted_recovery_prob=p_rec_retry,
            predicted_natural_prob=p_natural,
            predicted_iev_inr=round(iev_retry, 2),
            confidence=0.85,
            reason_codes=["adaptive_timing_retry", f"rail_health_{env.rail_health_score}"]
        ))
        
        # 3. Evaluate Payment Link Notification
        # Respect DND preferences
        channel = "EMAIL" if cust.dnd_active else "SMS"
        cost_notify = (settings.email_cost_inr if channel == "EMAIL" else settings.sms_cost_inr) + settings.customer_annoyance_penalty_inr
        
        if code in ["BAD_REQUEST_INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED"]:
            p_rec_notify = 0.65
        else:
            p_rec_notify = 0.40
        
        p_inc_notify = max(0.0, p_rec_notify - p_natural)
        iev_notify = (p_inc_notify * amount_inr) - cost_notify
        
        candidates.append(PolicyDecision(
            action_type=ActionType.NOTIFY_PAYMENT_LINK,
            action_parameters=NotifyParameters(channel=channel).model_dump(),
            predicted_recovery_prob=p_rec_notify,
            predicted_natural_prob=p_natural,
            predicted_iev_inr=round(iev_notify, 2),
            confidence=0.80,
            reason_codes=["actionable_notification", f"channel_{channel}"]
        ))
        
        # 4. Evaluate Support Escalation (Only if Amount >= ₹25,000)
        if amount_inr >= 25000:
            p_rec_esc = 0.70
            p_inc_esc = max(0.0, p_rec_esc - p_natural)
            iev_esc = (p_inc_esc * amount_inr) - settings.human_ops_cost_inr
            candidates.append(PolicyDecision(
                action_type=ActionType.ESCALATE_TO_SUPPORT,
                action_parameters=EscalateParameters(reason="vip_high_value_recovery").model_dump(),
                predicted_recovery_prob=p_rec_esc,
                predicted_natural_prob=p_natural,
                predicted_iev_inr=round(iev_esc, 2),
                confidence=0.90,
                reason_codes=["high_value_escalation"]
            ))
        
        # 5. Evaluate No Action
        candidates.append(PolicyDecision(
            action_type=ActionType.NO_ACTION,
            action_parameters=NoActionParameters(reason="zero_incremental_value").model_dump(),
            predicted_recovery_prob=p_natural,
            predicted_natural_prob=p_natural,
            predicted_iev_inr=0.0,
            confidence=1.0,
            reason_codes=["zero_cost_baseline"]
        ))
        
        # Sort descending by predicted IEV
        candidates.sort(key=lambda c: c.predicted_iev_inr, reverse=True)
        best = candidates[0]
        
        # If best IEV <= 0, fall back to No Action
        if best.predicted_iev_inr <= 0:
            for c in candidates:
                if c.action_type == ActionType.NO_ACTION:
                    return c
        return best
