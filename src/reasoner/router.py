"""Selective Ambiguity Router - Separates Deterministic Fast-Path from LLM Reasoning."""

from typing import Tuple
from eval.schemas import ObservableCase
from src.core.economics import HARD_DECLINE_CODES


class AmbiguityClassifier:
    """Classifies incoming failure cases to selectively trigger LLM reasoning only when required."""
    
    @staticmethod
    def should_route_to_llm(case: ObservableCase) -> Tuple[bool, str]:
        """Returns (needs_llm, reason). Fast-paths known cases to avoid unnecessary LLM costs."""
        code = case.payment.failure_code
        amount = case.payment.amount_inr
        env = case.environment
        cust = case.customer
        
        # 1. Fast Path: Hard declines are permanently non-recoverable (0% LLM utility)
        if code in HARD_DECLINE_CODES:
            return False, "fast_path_hard_decline"
        
        # 2. Fast Path: Low-value clear network timeout on healthy rail (deterministic retry wins)
        if code in ["BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR"] and env.rail_health_score >= 80 and amount < 10000:
            return False, "fast_path_clear_technical_timeout"
        
        # 3. Slow Path (LLM): Generic bank decline on high-tenure / VIP customer (ambiguous intent)
        if code in ["BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "BANK_TECHNICAL_ERROR"]:
            if cust.tenure_days > 180 or cust.historical_recovery_rate > 0.70 or amount >= 10000:
                return True, "ambiguous_bank_decline_loyal_customer"
        
        # 4. Slow Path (LLM): Borderline rail health or conflicting environmental telemetry
        if 45 <= env.rail_health_score <= 75:
            return True, "conflicting_rail_health_telemetry"
        
        # 5. Slow Path (LLM): High-value transactions (>= ₹20,000) requiring nuanced recovery routing
        if amount >= 20000:
            return True, "high_value_transaction_nuanced_routing"
        
        # 6. Default to Deterministic Fast Path
        return False, "fast_path_standard_heuristic"


ambiguity_router = AmbiguityClassifier()
