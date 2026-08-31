"""Deterministic Synthetic Transaction Population Generator."""

import random
import uuid
from typing import List
from eval.schemas import (
    CustomerContext,
    EnvironmentContext,
    LatencyBucket,
    ObservableCase,
    PaymentContext,
    TransactionRecord,
)
from eval.world import HiddenWorldPhysics


DECLINE_CODES_DISTRIBUTION = [
    ("BAD_REQUEST_PAYMENT_TIMED_OUT", "Bank gateway response timed out", 0.25),
    ("GATEWAY_ERROR", "Temporary network failure between merchant and switch", 0.15),
    ("BAD_REQUEST_INSUFFICIENT_FUNDS", "Customer account has insufficient funds", 0.20),
    ("BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED", "3D Secure 2FA verification timeout or failure", 0.15),
    ("BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Generic issuer bank policy decline", 0.10),
    ("BAD_REQUEST_CARD_STOLEN", "Card reported stolen or lost", 0.05),
    ("BAD_REQUEST_PAYMENT_CARD_INVALID", "Invalid card number or expired credentials", 0.05),
    ("BANK_TECHNICAL_ERROR", "Core banking switch internal server error", 0.05),
]


class SyntheticPopulationGenerator:
    """Generates realistic transaction populations with decoupled latent ground truth."""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
    
    def _sample_decline_code(self) -> tuple[str, str]:
        r = self.rng.random()
        cumulative = 0.0
        for code, desc, weight in DECLINE_CODES_DISTRIBUTION:
            cumulative += weight
            if r <= cumulative:
                return code, desc
        return DECLINE_CODES_DISTRIBUTION[0][0], DECLINE_CODES_DISTRIBUTION[0][1]
    
    def generate_case(self, index: int) -> TransactionRecord:
        case_id = f"case_eval_{self.seed}_{index:06d}"
        payment_id = f"pay_{self.seed}_{index:06d}"
        order_id = f"order_{self.seed}_{index:06d}"
        customer_id = f"cust_{self.rng.randint(1000, 99999):05d}"
        
        # 1. Amount distribution: Log-normal (mostly ₹500 - ₹5000, with VIP cases reaching ₹50,000+)
        base_amount = int(self.rng.lognormvariate(mu=7.2, sigma=0.9)) + 100
        amount_inr = round(max(99.0, min(150000.0, float(base_amount))), 2)
        amount_paise = int(amount_inr * 100)
        
        # 2. Payment Method
        method_roll = self.rng.random()
        if method_roll < 0.55:
            method = "upi"
        elif method_roll < 0.90:
            method = "card"
        else:
            method = "netbanking"
        
        # 3. Decline Code
        decline_code, decline_desc = self._sample_decline_code()
        
        # 4. Environment & System Health
        # 15% of transactions occur during a bank/rail latency spike or downtime
        is_degraded = self.rng.random() < 0.15
        if is_degraded:
            rail_health = self.rng.randint(10, 45)
            latency_bucket = LatencyBucket.OUTAGE if rail_health < 25 else LatencyBucket.ELEVATED
            recent_fail_rate = round(self.rng.uniform(0.35, 0.85), 3)
        else:
            rail_health = self.rng.randint(80, 100)
            latency_bucket = LatencyBucket.NORMAL
            recent_fail_rate = round(self.rng.uniform(0.01, 0.08), 3)
        
        # 5. Customer Profile
        tenure_days = self.rng.randint(1, 1200)
        hist_attempts = self.rng.randint(1, 50)
        hist_successes = int(hist_attempts * self.rng.uniform(0.60, 0.98))
        hist_recovery_rate = round(hist_successes / max(1, hist_attempts), 3)
        avg_order_value = round(self.rng.uniform(500.0, 15000.0), 2)
        dnd_active = self.rng.random() < 0.08  # 8% of customers on DND list
        
        # 6. Build Observable Context
        observable = ObservableCase(
            case_id=case_id,
            payment=PaymentContext(
                payment_id=payment_id,
                order_id=order_id,
                merchant_id="merch_buildathon_eval",
                amount_paise=amount_paise,
                amount_inr=amount_inr,
                currency="INR",
                method=method,
                failure_code=decline_code,
                failure_description=decline_desc,
                attempt_number=1,
                gateway="HDFC" if method == "card" else "NPCI_UPI",
                issuer_bank="HDFC"
            ),
            customer=CustomerContext(
                customer_id=customer_id,
                tenure_days=tenure_days,
                historical_attempts=hist_attempts,
                historical_successes=hist_successes,
                historical_recovery_rate=hist_recovery_rate,
                avg_order_value_inr=avg_order_value,
                preferred_method=method,
                dnd_active=dnd_active
            ),
            environment=EnvironmentContext(
                rail_health_score=rail_health,
                is_downtime_active=is_degraded,
                latency_bucket=latency_bucket,
                recent_rail_failure_rate=recent_fail_rate
            )
        )
        
        # 7. Generate Independent Latent Ground Truth Physics
        latent = HiddenWorldPhysics.generate_latent_ground_truth(
            case_id=case_id,
            failure_code=decline_code,
            amount_inr=amount_inr,
            rail_health_score=rail_health,
            tenure_days=tenure_days,
            rng=self.rng
        )
        
        return TransactionRecord(observable=observable, latent=latent)
    
    def generate_population(self, n: int) -> List[TransactionRecord]:
        """Generates n paired transaction records deterministically."""
        return [self.generate_case(i) for i in range(n)]
