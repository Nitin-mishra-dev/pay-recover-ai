"""Economic Evaluation Engine - Candidate Action Generation & IEV Scoring."""

from typing import List, Optional
from src.config import settings
from src.models.actions import (
    ActionType,
    CandidateAction,
    EscalateParameters,
    NoActionParameters,
    NotifyParameters,
    RetryParameters,
)
from src.models.state import PaymentCase


HARD_DECLINE_CODES = {
    "BAD_REQUEST_PAYMENT_CARD_INVALID",
    "BAD_REQUEST_CARD_STOLEN",
    "BAD_REQUEST_CARD_LOST",
    "BAD_REQUEST_PAYMENT_ACCOUNT_CLOSED",
    "BAD_REQUEST_FRAUD_SUSPECTED"
}

SOFT_DECLINE_CODES = {
    "BAD_REQUEST_PAYMENT_TIMED_OUT",
    "GATEWAY_ERROR",
    "BANK_TECHNICAL_ERROR",
    "BAD_REQUEST_INSUFFICIENT_FUNDS",
    "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED",
    "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK"
}


class EconomicDecisionEngine:
    """Evaluates candidate recovery actions, estimates incremental uplift, and selects max-IEV action."""
    
    def __init__(self):
        pass
    
    def estimate_natural_recovery(self, case: PaymentCase) -> float:
        """Estimates organic reattempt probability if merchant takes no action."""
        if case.error_code in HARD_DECLINE_CODES:
            return 0.0
        # Customers naturally re-attempt small purchases more frequently
        amount_inr = case.amount_paise / 100.0
        if amount_inr < 1000:
            return 0.20
        elif amount_inr < 10000:
            return 0.10
        return 0.05
    
    def generate_and_score_candidates(
        self,
        case: PaymentCase,
        is_degraded: bool = False,
        adaptive_delay: int = 300
    ) -> List[CandidateAction]:
        """Produces ranked candidate actions with explicit IEV calculations."""
        amount_inr = case.amount_paise / 100.0
        p_natural = self.estimate_natural_recovery(case)
        candidates: List[CandidateAction] = []
        
        # 1. Hard decline filter
        if case.error_code in HARD_DECLINE_CODES:
            candidates.append(CandidateAction(
                action_type=ActionType.NO_ACTION,
                parameters=NoActionParameters(reason=f"hard_decline_{case.error_code}").model_dump(),
                predicted_recovery_prob=0.0,
                natural_recovery_prob=0.0,
                incremental_prob=0.0,
                gross_expected_value_inr=0.0,
                direct_cost_inr=0.0,
                risk_penalty_inr=0.0,
                expected_incremental_value_inr=0.0,
                reason_codes=["permanent_hard_decline", "zero_recovery_possible"]
            ))
            return candidates
        
        # 2. Candidate: Smart Retry (Immediate or Adaptive Delay)
        if case.attempt_count < settings.max_retries_ceiling:
            delay = adaptive_delay if is_degraded else 300
            # Higher recovery when delay is applied during degraded rail
            p_rec_retry = 0.75 if (not is_degraded or delay >= 1800) else 0.20
            p_inc_retry = max(0.0, p_rec_retry - p_natural)
            cost_retry = settings.direct_retry_cost_inr
            risk_retry = 0.0  # Soft decline has low fraud risk
            iev_retry = (p_inc_retry * amount_inr) - cost_retry - risk_retry
            
            candidates.append(CandidateAction(
                action_type=ActionType.RETRY_PAYMENT,
                parameters=RetryParameters(delay_seconds=delay, attempt_number=case.attempt_count + 1).model_dump(),
                predicted_recovery_prob=p_rec_retry,
                natural_recovery_prob=p_natural,
                incremental_prob=p_inc_retry,
                gross_expected_value_inr=round(p_inc_retry * amount_inr, 2),
                direct_cost_inr=cost_retry,
                risk_penalty_inr=risk_retry,
                expected_incremental_value_inr=round(iev_retry, 2),
                reason_codes=["soft_decline_retriable", "high_uplift_vs_natural"]
            ))
        
        # 3. Candidate: Payment Link Notification
        if case.notification_count < 2 and (case.customer_contact or case.customer_email):
            channel = "SMS" if case.customer_contact else "EMAIL"
            cost_channel = settings.sms_cost_inr if channel == "SMS" else settings.email_cost_inr
            total_cost_notify = cost_channel + settings.customer_annoyance_penalty_inr
            
            p_rec_notify = 0.45
            p_inc_notify = max(0.0, p_rec_notify - p_natural)
            iev_notify = (p_inc_notify * amount_inr) - total_cost_notify
            
            candidates.append(CandidateAction(
                action_type=ActionType.NOTIFY_PAYMENT_LINK,
                parameters=NotifyParameters(channel=channel).model_dump(),
                predicted_recovery_prob=p_rec_notify,
                natural_recovery_prob=p_natural,
                incremental_prob=p_inc_notify,
                gross_expected_value_inr=round(p_inc_notify * amount_inr, 2),
                direct_cost_inr=total_cost_notify,
                risk_penalty_inr=0.0,
                expected_incremental_value_inr=round(iev_notify, 2),
                reason_codes=["customer_actionable_notification"]
            ))
        
        # 4. Candidate: Escalate to Support (for High-Value Cases)
        if amount_inr >= 25000:
            p_rec_esc = 0.65
            p_inc_esc = max(0.0, p_rec_esc - p_natural)
            cost_esc = settings.human_ops_cost_inr
            iev_esc = (p_inc_esc * amount_inr) - cost_esc
            
            candidates.append(CandidateAction(
                action_type=ActionType.ESCALATE_TO_SUPPORT,
                parameters=EscalateParameters(reason="high_value_transaction").model_dump(),
                predicted_recovery_prob=p_rec_esc,
                natural_recovery_prob=p_natural,
                incremental_prob=p_inc_esc,
                gross_expected_value_inr=round(p_inc_esc * amount_inr, 2),
                direct_cost_inr=cost_esc,
                risk_penalty_inr=0.0,
                expected_incremental_value_inr=round(iev_esc, 2),
                reason_codes=["high_value_vip_escalation"]
            ))
        
        # 5. Fallback: No Action
        candidates.append(CandidateAction(
            action_type=ActionType.NO_ACTION,
            parameters=NoActionParameters().model_dump(),
            predicted_recovery_prob=p_natural,
            natural_recovery_prob=p_natural,
            incremental_prob=0.0,
            gross_expected_value_inr=0.0,
            direct_cost_inr=0.0,
            risk_penalty_inr=0.0,
            expected_incremental_value_inr=0.0,
            reason_codes=["baseline_no_action"]
        ))
        
        # Sort candidates descending by IEV
        candidates.sort(key=lambda c: c.expected_incremental_value_inr, reverse=True)
        return candidates
    
    def select_best_action(self, candidates: List[CandidateAction]) -> CandidateAction:
        """Selects the candidate with maximum IEV, or No Action if all IEV <= 0."""
        for candidate in candidates:
            if candidate.expected_incremental_value_inr > 0:
                return candidate
        # If no positive IEV, pick no_action
        for candidate in candidates:
            if candidate.action_type == ActionType.NO_ACTION:
                return candidate
        return candidates[0]


economic_engine = EconomicDecisionEngine()
