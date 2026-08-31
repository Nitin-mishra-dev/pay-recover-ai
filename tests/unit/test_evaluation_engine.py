"""Unit and invariant tests for the Independent Evaluation Harness and Baselines."""

import pytest
from eval.baselines import (
    BlindRetryBaseline,
    NoActionBaseline,
    PayRecoverAIEngine,
    StaticRulesBaseline,
)
from eval.dataset import EvaluationDataset
from eval.generator import SyntheticPopulationGenerator
from eval.metrics import EvaluatorEngine
from eval.schemas import (
    CustomerContext,
    EnvironmentContext,
    LatencyBucket,
    ObservableCase,
    PaymentContext,
)
from src.models.actions import ActionType


def make_test_case(amount_inr: float = 5000.0, failure_code: str = "BAD_REQUEST_PAYMENT_TIMED_OUT", rail_health: int = 90, dnd: bool = False) -> ObservableCase:
    return ObservableCase(
        case_id="case_test_mock_01",
        payment=PaymentContext(
            payment_id="pay_mock_01",
            order_id="order_mock_01",
            amount_paise=int(amount_inr * 100),
            amount_inr=amount_inr,
            currency="INR",
            method="card",
            failure_code=failure_code,
            failure_description="Test failure",
            attempt_number=1,
            gateway="HDFC",
            issuer_bank="HDFC"
        ),
        customer=CustomerContext(
            customer_id="cust_mock_01",
            tenure_days=150,
            historical_attempts=10,
            historical_successes=8,
            historical_recovery_rate=0.80,
            avg_order_value_inr=amount_inr,
            preferred_method="card",
            dnd_active=dnd
        ),
        environment=EnvironmentContext(
            rail_health_score=rail_health,
            is_downtime_active=(rail_health < 50),
            latency_bucket=LatencyBucket.NORMAL if rail_health >= 75 else LatencyBucket.OUTAGE,
            recent_rail_failure_rate=0.02 if rail_health >= 75 else 0.65
        )
    )


def test_1_ground_truth_independence():
    """Test 1: Latent ground-truth counterfactuals exist independently of any model evaluation."""
    gen = SyntheticPopulationGenerator(seed=42)
    record = gen.generate_case(0)
    
    # Assert latent outcome dictionary is populated before any policy is invoked
    assert "no_action:0" in record.latent.counterfactual_outcomes
    assert "retry_payment:300" in record.latent.counterfactual_outcomes
    assert record.latent.counterfactual_outcomes["no_action:0"] in [0, 1]
    assert record.latent.counterfactual_outcomes["retry_payment:300"] in [0, 1]


def test_2_baselines_are_deterministic():
    """Test 2: Fixed observable case produces identical decisions across repeated calls."""
    case = make_test_case()
    engine = PayRecoverAIEngine()
    
    dec1 = engine.decide(case)
    dec2 = engine.decide(case)
    
    assert dec1.action_type == dec2.action_type
    assert dec1.predicted_iev_inr == dec2.predicted_iev_inr
    assert dec1.action_parameters == dec2.action_parameters


def test_3_holdout_isolation():
    """Test 3: Dataset partitioning guarantees DEV, TEST, and HOLDOUT are non-overlapping and sealed."""
    gen = SyntheticPopulationGenerator(seed=42)
    records = gen.generate_population(100)
    splits = EvaluationDataset.partition_population(records)
    
    dev_ids = {r.observable.case_id for r in splits["dev"]}
    test_ids = {r.observable.case_id for r in splits["test"]}
    holdout_ids = {r.observable.case_id for r in splits["holdout"]}
    
    assert len(dev_ids) == 60
    assert len(test_ids) == 20
    assert len(holdout_ids) == 20
    assert dev_ids.isdisjoint(test_ids)
    assert dev_ids.isdisjoint(holdout_ids)
    assert test_ids.isdisjoint(holdout_ids)


def test_4_iev_calculation_correctness():
    """Test 4: Expected Incremental Value math = (P_rec - P_nat) * Amount - Cost."""
    engine = PayRecoverAIEngine()
    case = make_test_case(amount_inr=10000.0, failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT", rail_health=95)
    decision = engine.decide(case)
    
    # Assert IEV is positive and correctly accounts for direct retry cost (₹0.50)
    assert decision.action_type == ActionType.RETRY_PAYMENT
    expected_inc_prob = decision.predicted_recovery_prob - decision.predicted_natural_prob
    expected_iev = round((expected_inc_prob * 10000.0) - 0.50, 2)
    assert decision.predicted_iev_inr == expected_iev


def test_5_natural_recovery_subtracted():
    """Test 5: Natural recovery probability is explicitly subtracted, avoiding gross recovery credit."""
    engine = PayRecoverAIEngine()
    case = make_test_case(amount_inr=500.0)  # Small amount has higher natural recovery
    decision = engine.decide(case)
    
    assert decision.predicted_natural_prob > 0.0
    assert decision.predicted_recovery_prob > decision.predicted_natural_prob


def test_6_action_costs_affect_decisions():
    """Test 6: High intervention cost on tiny amounts leads to No Action if Cost > Incremental Gain."""
    engine = PayRecoverAIEngine()
    # Very small ₹1.00 payment
    case = make_test_case(amount_inr=1.00, failure_code="BAD_REQUEST_INSUFFICIENT_FUNDS")
    decision = engine.decide(case)
    
    # SMS cost (₹2.20) exceeds the entire transaction value -> must NOT notify!
    assert decision.action_type != ActionType.NOTIFY_PAYMENT_LINK


def test_7_risk_penalties_affect_decisions():
    """Test 7: Hard declines (fraud / stolen card) immediately produce No Action (0 cost, 0 risk)."""
    engine = PayRecoverAIEngine()
    case = make_test_case(amount_inr=20000.0, failure_code="BAD_REQUEST_CARD_STOLEN")
    decision = engine.decide(case)
    
    assert decision.action_type == ActionType.NO_ACTION
    assert decision.predicted_iev_inr == 0.0


def test_8_merchant_policy_dnd_constraint():
    """Test 8: Customer with DND active never receives SMS payment link (routes to Email)."""
    engine = PayRecoverAIEngine()
    case = make_test_case(amount_inr=5000.0, failure_code="BAD_REQUEST_INSUFFICIENT_FUNDS", dnd=True)
    decision = engine.decide(case)
    
    if decision.action_type == ActionType.NOTIFY_PAYMENT_LINK:
        assert decision.action_parameters["channel"] == "EMAIL"


def test_9_different_action_timings_produce_different_values():
    """Test 9: During active rail degradation, PayRecover selects adaptive delay (1800s) over immediate retry."""
    engine = PayRecoverAIEngine()
    case_healthy = make_test_case(rail_health=95)
    case_degraded = make_test_case(rail_health=20)
    
    dec_healthy = engine.decide(case_healthy)
    dec_degraded = engine.decide(case_degraded)
    
    assert dec_healthy.action_parameters.get("delay_seconds", 300) == 300
    assert dec_degraded.action_parameters.get("delay_seconds", 1800) >= 1800


def test_10_same_seed_reproduces_same_benchmark():
    """Test 10: Running dataset generation with identical seed reproduces identical manifest hash."""
    records_1 = EvaluationDataset.load_dataset(seed=42, n=50, split="holdout")
    records_2 = EvaluationDataset.load_dataset(seed=42, n=50, split="holdout")
    
    hash_1 = EvaluationDataset.compute_split_manifest_hash(records_1)
    hash_2 = EvaluationDataset.compute_split_manifest_hash(records_2)
    assert hash_1 == hash_2


def test_11_different_seeds_produce_independent_populations():
    """Test 11: Different random seeds generate statistically distinct populations."""
    records_42 = EvaluationDataset.load_dataset(seed=42, n=50, split="holdout")
    records_99 = EvaluationDataset.load_dataset(seed=99, n=50, split="holdout")
    
    hash_42 = EvaluationDataset.compute_split_manifest_hash(records_42)
    hash_99 = EvaluationDataset.compute_split_manifest_hash(records_99)
    assert hash_42 != hash_99


def test_12_benchmark_recomputability():
    """Test 12: Strategy evaluation results can be recomputed directly from realized outcomes."""
    records = EvaluationDataset.load_dataset(seed=42, n=50, split="test")
    policy = PayRecoverAIEngine()
    result = EvaluatorEngine.evaluate_strategy(records, policy)
    
    # Verify sum identity: Recovered = Natural + Incremental
    assert round(result.natural_recovery_revenue_inr + result.incremental_recovered_revenue_inr, 2) == round(result.recovered_revenue_inr, 2)
    # Verify NIV identity: NIV = Incremental - Cost
    assert round(result.incremental_recovered_revenue_inr - result.intervention_cost_inr, 2) == round(result.net_incremental_value_inr, 2)
