"""Independent Counterfactual Simulation Environment & Hidden World Physics."""

import random
from typing import Dict, Tuple
from eval.schemas import LatentGroundTruth, ObservableCase, WorldVersion


class HiddenWorldPhysics:
    """Calculates true latent recovery probabilities and samples counterfactual outcomes."""
    
    @staticmethod
    def generate_latent_ground_truth(
        case_id: str,
        failure_code: str,
        amount_inr: float,
        rail_health_score: int,
        tenure_days: int,
        rng: random.Random,
        world_version: WorldVersion = WorldVersion.V1_STANDARD
    ) -> LatentGroundTruth:
        """Generates hidden latent variables and counterfactual outcomes for all possible actions."""
        
        # 1. Latent Fraud / Card State
        is_hard_decline = failure_code in [
            "BAD_REQUEST_PAYMENT_CARD_INVALID",
            "BAD_REQUEST_CARD_STOLEN",
            "BAD_REQUEST_CARD_LOST",
            "BAD_REQUEST_PAYMENT_ACCOUNT_CLOSED",
            "BAD_REQUEST_FRAUD_SUSPECTED"
        ]
        is_fraud_true = is_hard_decline and (rng.random() < 0.85)
        is_card_permanently_dead = is_hard_decline
        
        # 2. Latent Customer Intent
        # Higher tenure and past frequency increase true purchase intent
        base_intent = 0.50 + min(0.35, tenure_days / 1000.0)
        true_payer_intent = max(0.05, min(0.95, base_intent + rng.gauss(0, 0.10)))
        
        # 3. Latent Outage Duration
        if rail_health_score < 40:
            true_outage_duration_seconds = int(rng.expovariate(1.0 / 1800.0)) + 600  # 10m to 60m outage
        elif rail_health_score < 75:
            true_outage_duration_seconds = int(rng.expovariate(1.0 / 300.0)) + 60    # 1m to 10m glitch
        else:
            true_outage_duration_seconds = 0                                         # Healthy rail
        
        # 4. Latent Natural Organic Recovery (No Action)
        if is_card_permanently_dead:
            p_natural = 0.0
        else:
            if world_version == WorldVersion.V3_HIGH_NATURAL_HIGH_COST:
                # High natural organic recovery distribution
                if amount_inr < 1000:
                    p_natural = 0.55 * true_payer_intent
                elif amount_inr < 10000:
                    p_natural = 0.40 * true_payer_intent
                else:
                    p_natural = 0.25 * true_payer_intent
            else:
                # Small amounts have higher organic reattempts by users (V1 & V2)
                if amount_inr < 1000:
                    p_natural = 0.15 * true_payer_intent
                elif amount_inr < 10000:
                    p_natural = 0.08 * true_payer_intent
                else:
                    p_natural = 0.03 * true_payer_intent
        
        # 5. Compute Latent Probabilities for All Interventions
        latent_probs: Dict[str, float] = {}
        latent_probs["no_action:0"] = p_natural
        
        if is_card_permanently_dead:
            # Permanent declines have 0% recovery across all retry/notify actions
            latent_probs["retry_payment:0"] = 0.0
            latent_probs["retry_payment:300"] = 0.0
            latent_probs["retry_payment:1800"] = 0.0
            latent_probs["retry_payment:7200"] = 0.0
            latent_probs["notify_payment_link:SMS"] = 0.0
            latent_probs["notify_payment_link:EMAIL"] = 0.0
            latent_probs["escalate_to_support:0"] = 0.0
        else:
            # A. Retry actions at different delays
            for delay in [0, 300, 1800, 7200]:
                if delay < true_outage_duration_seconds:
                    # Retrying while outage is active almost always fails
                    p_retry = max(p_natural, 0.05 * true_payer_intent)
                else:
                    # Outage is over
                    if world_version == WorldVersion.V2_WEAK_RETRY_STRONG_NOTIFY:
                        # Transient retry is significantly weaker in V2
                        if failure_code in ["BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR", "BANK_TECHNICAL_ERROR"]:
                            p_retry = max(p_natural, 0.45 * true_payer_intent)
                        elif failure_code in ["BAD_REQUEST_INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK"]:
                            p_retry = max(p_natural, 0.15 * true_payer_intent)
                        else:
                            p_retry = max(p_natural, 0.25 * true_payer_intent)
                    else:
                        # Standard / High Cost retry (V1 & V3)
                        if failure_code in ["BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR", "BANK_TECHNICAL_ERROR"]:
                            p_retry = max(p_natural, 0.85 * true_payer_intent)
                        elif failure_code in ["BAD_REQUEST_INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK"]:
                            p_retry = max(p_natural, 0.25 * true_payer_intent)
                        else:
                            p_retry = max(p_natural, 0.40 * true_payer_intent)
                
                # Decay factor for very late retries (users lose patience)
                decay = 1.0 if delay <= 1800 else 0.90
                latent_probs[f"retry_payment:{delay}"] = min(0.98, p_retry * decay)
            
            # B. Customer Notification Links
            if world_version == WorldVersion.V2_WEAK_RETRY_STRONG_NOTIFY:
                # Customer notification response is stronger in V2
                if failure_code in ["BAD_REQUEST_INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED"]:
                    latent_probs["notify_payment_link:SMS"] = min(0.98, 0.90 * true_payer_intent)
                    latent_probs["notify_payment_link:EMAIL"] = min(0.95, 0.75 * true_payer_intent)
                else:
                    latent_probs["notify_payment_link:SMS"] = min(0.90, 0.65 * true_payer_intent)
                    latent_probs["notify_payment_link:EMAIL"] = min(0.85, 0.50 * true_payer_intent)
            else:
                if failure_code in ["BAD_REQUEST_INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED"]:
                    latent_probs["notify_payment_link:SMS"] = min(0.95, 0.70 * true_payer_intent)
                    latent_probs["notify_payment_link:EMAIL"] = min(0.90, 0.55 * true_payer_intent)
                else:
                    latent_probs["notify_payment_link:SMS"] = min(0.85, 0.45 * true_payer_intent)
                    latent_probs["notify_payment_link:EMAIL"] = min(0.80, 0.35 * true_payer_intent)
            
            # C. Support Escalation
            latent_probs["escalate_to_support:0"] = min(0.95, 0.75 * true_payer_intent)
        
        # 6. Sample Independent Counterfactual Realizations Y in {0, 1}
        # Using a separate RNG state for outcome realization guarantees outcome independence
        counterfactual_outcomes: Dict[str, int] = {}
        for action_key, prob in latent_probs.items():
            counterfactual_outcomes[action_key] = 1 if rng.random() < prob else 0
        
        return LatentGroundTruth(
            latent_case_id=case_id,
            world_version=world_version,
            is_fraud_true=is_fraud_true,
            is_card_permanently_dead=is_card_permanently_dead,
            true_payer_intent_score=round(true_payer_intent, 4),
            true_outage_duration_seconds=true_outage_duration_seconds,
            counterfactual_outcomes=counterfactual_outcomes,
            latent_probabilities={k: round(v, 4) for k, v in latent_probs.items()}
        )
