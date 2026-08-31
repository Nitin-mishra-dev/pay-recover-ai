"""The Locked Baseline Strategies and Oracle Upper Bound for Economic Benchmarking."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from eval.schemas import (
    LatentGroundTruth,
    MERCHANT_RISK_PROFILES,
    MerchantRiskProfile,
    ObservableCase,
    PolicyDecision,
    WorldVersion,
)
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
    def decide(
        self,
        case: ObservableCase,
        latent: Optional[LatentGroundTruth] = None
    ) -> PolicyDecision:
        """Evaluates observable context (and optional sealed latent truth for Oracle) and selects a recovery action."""
        pass


class NoActionBaseline(BaseRecoveryPolicy):
    """Baseline 0: Passive Control Floor (Takes no action; zero cost)."""
    
    @property
    def name(self) -> str:
        return "Baseline 0: No Action"
    
    @property
    def description(self) -> str:
        return "Complete inaction upon failure. Realizes only natural customer reattempts."
    
    def decide(
        self,
        case: ObservableCase,
        latent: Optional[LatentGroundTruth] = None
    ) -> PolicyDecision:
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
    
    def decide(
        self,
        case: ObservableCase,
        latent: Optional[LatentGroundTruth] = None
    ) -> PolicyDecision:
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
    
    def decide(
        self,
        case: ObservableCase,
        latent: Optional[LatentGroundTruth] = None
    ) -> PolicyDecision:
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
    """Baseline 3: PayRecover AI (Adaptive Counterfactual Incremental Value Decision Engine)."""
    
    def __init__(
        self,
        risk_profile: Optional[MerchantRiskProfile] = None,
        custom_natural_rate: Optional[float] = None
    ):
        self.risk_profile = risk_profile
        self.custom_natural_rate = custom_natural_rate
    
    @property
    def name(self) -> str:
        return "Baseline 3: PayRecover AI"
    
    @property
    def description(self) -> str:
        return "Adaptive decision layer maximizing Net Incremental Value with degradation-aware timing."
    
    def _estimate_natural_recovery(self, case: ObservableCase) -> float:
        """Estimates organic baseline recovery probability."""
        if self.custom_natural_rate is not None:
            return self.custom_natural_rate
        if case.payment.failure_code in HARD_DECLINE_CODES:
            return 0.0
        amount = case.payment.amount_inr
        tenure_bonus = min(0.08, case.customer.tenure_days / 5000.0)
        if amount < 1000:
            return 0.15 + tenure_bonus
        elif amount < 10000:
            return 0.08 + tenure_bonus
        return 0.03 + tenure_bonus
    
    def decide(
        self,
        case: ObservableCase,
        latent: Optional[LatentGroundTruth] = None
    ) -> PolicyDecision:
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
        
        # Merchant Risk Profile Constraints
        max_attempts = self.risk_profile.max_attempts if self.risk_profile else 3
        allow_sms = self.risk_profile.allow_sms if self.risk_profile else True
        max_auto_value = self.risk_profile.max_auto_value if self.risk_profile else float("inf")
        is_exceeding_auto_value = amount_inr > max_auto_value
        
        # 2. Evaluate Smart Retry (Immediate vs Adaptive Delay based on Rail Health)
        is_degraded = env.is_downtime_active or (env.rail_health_score < 60)
        delay_chosen = 1800 if is_degraded else 300
        
        # Only evaluate automated retry if within attempt limit and auto value threshold
        if case.payment.attempt_number <= max_attempts and not is_exceeding_auto_value:
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
                action_parameters=RetryParameters(delay_seconds=delay_chosen, attempt_number=case.payment.attempt_number).model_dump(),
                predicted_recovery_prob=p_rec_retry,
                predicted_natural_prob=p_natural,
                predicted_iev_inr=round(iev_retry, 2),
                confidence=0.85,
                reason_codes=["adaptive_timing_retry", f"rail_health_{env.rail_health_score}"]
            ))
        
        # 3. Evaluate Payment Link Notification
        if not is_exceeding_auto_value:
            # Respect DND and merchant risk profile SMS policy
            channel = "EMAIL" if (cust.dnd_active or not allow_sms) else "SMS"
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
        
        # 4. Evaluate Support Escalation (VIP high-value or exceeded merchant auto value threshold)
        if amount_inr >= 25000 or (is_exceeding_auto_value and amount_inr >= 5000):
            p_rec_esc = 0.70
            p_inc_esc = max(0.0, p_rec_esc - p_natural)
            iev_esc = (p_inc_esc * amount_inr) - settings.human_ops_cost_inr
            candidates.append(PolicyDecision(
                action_type=ActionType.ESCALATE_TO_SUPPORT,
                action_parameters=EscalateParameters(reason="high_value_escalation").model_dump(),
                predicted_recovery_prob=p_rec_esc,
                predicted_natural_prob=p_natural,
                predicted_iev_inr=round(iev_esc, 2),
                confidence=0.90,
                reason_codes=["high_value_escalation"]
            ))
        
        # 5. Evaluate No Action Floor
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


class OracleUpperboundPolicy(BaseRecoveryPolicy):
    """Baseline 4: Oracle Upper Bound Policy (Perfect Latent Counterfactual Upper Bound)."""
    
    @property
    def name(self) -> str:
        return "Baseline 4: Oracle Upper Bound"
    
    @property
    def description(self) -> str:
        return "Theoretical upper bound with perfect knowledge of latent physics and counterfactual outcomes."
    
    def decide(
        self,
        case: ObservableCase,
        latent: Optional[LatentGroundTruth] = None
    ) -> PolicyDecision:
        amount_inr = case.payment.amount_inr
        
        if latent is None:
            return PolicyDecision(
                action_type=ActionType.NO_ACTION,
                action_parameters=NoActionParameters(reason="oracle_missing_latent").model_dump(),
                predicted_recovery_prob=0.0,
                predicted_natural_prob=0.0,
                predicted_iev_inr=0.0,
                confidence=1.0,
                reason_codes=["oracle_fallback_no_action"]
            )
        
        nat_y = latent.counterfactual_outcomes.get("no_action:0", 0)
        nat_rev = amount_inr if nat_y else 0.0
        
        # Costs per action type based on world version
        world_ver = latent.world_version
        if world_ver == WorldVersion.V3_HIGH_NATURAL_HIGH_COST:
            retry_cost = 1.50
            sms_cost = 1.50 + 4.00
            email_cost = 0.10 + 4.00
            escalate_cost = 150.00
        else:
            retry_cost = settings.direct_retry_cost_inr
            sms_cost = settings.sms_cost_inr + settings.customer_annoyance_penalty_inr
            email_cost = settings.email_cost_inr + settings.customer_annoyance_penalty_inr
            escalate_cost = settings.human_ops_cost_inr
        
        best_action_key = "no_action:0"
        best_niv = 0.0
        best_captured = bool(nat_y)
        
        for cand_key, cand_y in latent.counterfactual_outcomes.items():
            if cand_key == "no_action:0":
                continue
            
            if cand_key.startswith("retry_payment:"):
                cand_cost = retry_cost
            elif cand_key == "notify_payment_link:SMS":
                cand_cost = sms_cost
            elif cand_key == "notify_payment_link:EMAIL":
                cand_cost = email_cost
            elif cand_key.startswith("escalate_to_support:"):
                cand_cost = escalate_cost
            else:
                cand_cost = 0.0
            
            cand_rev = amount_inr if cand_y else 0.0
            cand_inc_rev = cand_rev - nat_rev
            risk_penalty = (amount_inr + settings.chargeback_loss_penalty_inr) if (latent.is_fraud_true and cand_y) else 0.0
            cand_niv = cand_inc_rev - cand_cost - risk_penalty
            
            if cand_niv > best_niv:
                best_niv = cand_niv
                best_action_key = cand_key
                best_captured = bool(cand_y)
        
        if best_action_key == "no_action:0" or best_niv <= 0:
            return PolicyDecision(
                action_type=ActionType.NO_ACTION,
                action_parameters=NoActionParameters(reason="oracle_optimal_no_action").model_dump(),
                predicted_recovery_prob=float(nat_y),
                predicted_natural_prob=float(nat_y),
                predicted_iev_inr=0.0,
                confidence=1.0,
                reason_codes=["oracle_counterfactual_optimal", "chosen_no_action"]
            )
        elif best_action_key.startswith("retry_payment:"):
            delay = int(best_action_key.split(":")[1])
            return PolicyDecision(
                action_type=ActionType.RETRY_PAYMENT,
                action_parameters=RetryParameters(delay_seconds=delay, attempt_number=1).model_dump(),
                predicted_recovery_prob=float(best_captured),
                predicted_natural_prob=float(nat_y),
                predicted_iev_inr=round(best_niv, 2),
                confidence=1.0,
                reason_codes=["oracle_counterfactual_optimal", f"chosen_{best_action_key}"]
            )
        elif best_action_key.startswith("notify_payment_link:"):
            ch = best_action_key.split(":")[1]
            return PolicyDecision(
                action_type=ActionType.NOTIFY_PAYMENT_LINK,
                action_parameters=NotifyParameters(channel=ch).model_dump(),
                predicted_recovery_prob=float(best_captured),
                predicted_natural_prob=float(nat_y),
                predicted_iev_inr=round(best_niv, 2),
                confidence=1.0,
                reason_codes=["oracle_counterfactual_optimal", f"chosen_{best_action_key}"]
            )
        elif best_action_key.startswith("escalate_to_support:"):
            return PolicyDecision(
                action_type=ActionType.ESCALATE_TO_SUPPORT,
                action_parameters=EscalateParameters(reason="oracle_optimal_escalation").model_dump(),
                predicted_recovery_prob=float(best_captured),
                predicted_natural_prob=float(nat_y),
                predicted_iev_inr=round(best_niv, 2),
                confidence=1.0,
                reason_codes=["oracle_counterfactual_optimal", "chosen_escalate_to_support"]
            )
        
        return PolicyDecision(
            action_type=ActionType.NO_ACTION,
            action_parameters=NoActionParameters(reason="oracle_fallback").model_dump(),
            predicted_recovery_prob=float(nat_y),
            predicted_natural_prob=float(nat_y),
            predicted_iev_inr=0.0,
            confidence=1.0,
            reason_codes=["oracle_fallback"]
        )
