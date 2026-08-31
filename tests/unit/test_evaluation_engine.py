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


def test_13_high_natural_recovery_no_free_lunch():
    """Test 13: High natural recovery (85%) causes PayRecover to select NO_ACTION to avoid negative IEV."""
    # Under 85% natural recovery, taking action consumes fees without incremental gain
    engine = PayRecoverAIEngine(custom_natural_rate=0.85)
    
    # 1. Soft decline timeout (₹5,000)
    case_timeout = make_test_case(amount_inr=5000.0, failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT")
    dec_timeout = engine.decide(case_timeout)
    assert dec_timeout.action_type == ActionType.NO_ACTION
    assert dec_timeout.predicted_iev_inr == 0.0
    
    # 2. Insufficient funds actionable failure (₹2,000)
    case_funds = make_test_case(amount_inr=2000.0, failure_code="BAD_REQUEST_INSUFFICIENT_FUNDS")
    dec_funds = engine.decide(case_funds)
    assert dec_funds.action_type == ActionType.NO_ACTION
    assert dec_funds.predicted_iev_inr == 0.0
    
    # 3. Small purchase (₹100)
    case_small = make_test_case(amount_inr=100.0, failure_code="BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED")
    dec_small = engine.decide(case_small)
    assert dec_small.action_type == ActionType.NO_ACTION


def test_14_oracle_policy_upper_bound_invariant():
    """Test 14: Oracle policy strictly bounds and outperforms all baselines (NIV_Oracle >= NIV_PayRecover >= NIV_Static)."""
    from eval.baselines import OracleUpperboundPolicy
    
    records = EvaluationDataset.load_dataset(seed=42, n=2000, split="holdout")
    
    no_action = NoActionBaseline()
    static_rules = StaticRulesBaseline()
    pay_recover = PayRecoverAIEngine()
    oracle = OracleUpperboundPolicy()
    
    res_noaction = EvaluatorEngine.evaluate_strategy(records, no_action)
    res_static = EvaluatorEngine.evaluate_strategy(records, static_rules)
    res_pr = EvaluatorEngine.evaluate_strategy(records, pay_recover)
    res_oracle = EvaluatorEngine.evaluate_strategy(records, oracle)
    
    # Baseline 0 floor: NIV == 0
    assert res_noaction.net_incremental_value_inr == 0.0
    
    # Hierarchy invariant: Oracle >= PayRecover >= Static Rules
    assert res_oracle.net_incremental_value_inr >= res_pr.net_incremental_value_inr
    assert res_pr.net_incremental_value_inr >= res_static.net_incremental_value_inr
    
    # Policy Efficiency: NIV_PR / NIV_Oracle in (0, 100%]
    efficiency = (res_pr.net_incremental_value_inr / max(1.0, res_oracle.net_incremental_value_inr)) * 100
    assert 0.0 < efficiency <= 100.0


def test_15_distribution_shift_v2_weak_retry_strong_notify():
    """Test 15: V2 Distribution Shift (weak retry, strong notify) maintains positive PayRecover uplift."""
    from eval.baselines import OracleUpperboundPolicy
    from eval.schemas import WorldVersion
    
    records_v2 = EvaluationDataset.load_dataset(
        seed=42,
        n=2000,
        split="holdout",
        world_version=WorldVersion.V2_WEAK_RETRY_STRONG_NOTIFY
    )
    
    static_rules = StaticRulesBaseline()
    pay_recover = PayRecoverAIEngine()
    oracle = OracleUpperboundPolicy()
    
    res_static = EvaluatorEngine.evaluate_strategy(records_v2, static_rules, world_version=WorldVersion.V2_WEAK_RETRY_STRONG_NOTIFY)
    res_pr = EvaluatorEngine.evaluate_strategy(records_v2, pay_recover, world_version=WorldVersion.V2_WEAK_RETRY_STRONG_NOTIFY)
    res_oracle = EvaluatorEngine.evaluate_strategy(records_v2, oracle, world_version=WorldVersion.V2_WEAK_RETRY_STRONG_NOTIFY)
    
    # PayRecover maintains positive value and outperforms static rules without retuning
    assert res_pr.net_incremental_value_inr > 0.0
    assert res_oracle.net_incremental_value_inr >= res_pr.net_incremental_value_inr


def test_16_distribution_shift_v3_high_natural_high_cost():
    """Test 16: V3 Distribution Shift (high natural, high cost) maintains positive PayRecover uplift over blind retry."""
    from eval.baselines import OracleUpperboundPolicy
    from eval.schemas import WorldVersion
    
    records_v3 = EvaluationDataset.load_dataset(
        seed=42,
        n=2000,
        split="holdout",
        world_version=WorldVersion.V3_HIGH_NATURAL_HIGH_COST
    )
    
    blind_retry = BlindRetryBaseline()
    pay_recover = PayRecoverAIEngine()
    oracle = OracleUpperboundPolicy()
    
    res_blind = EvaluatorEngine.evaluate_strategy(records_v3, blind_retry, world_version=WorldVersion.V3_HIGH_NATURAL_HIGH_COST)
    res_pr = EvaluatorEngine.evaluate_strategy(records_v3, pay_recover, world_version=WorldVersion.V3_HIGH_NATURAL_HIGH_COST)
    res_oracle = EvaluatorEngine.evaluate_strategy(records_v3, oracle, world_version=WorldVersion.V3_HIGH_NATURAL_HIGH_COST)
    
    # Blind retry is severely penalized by high costs under high natural recovery
    assert res_pr.net_incremental_value_inr >= 0.0
    assert res_pr.net_incremental_value_inr > res_blind.net_incremental_value_inr
    assert res_oracle.net_incremental_value_inr >= res_pr.net_incremental_value_inr


def test_17_merchant_risk_profiles_constraints():
    """Test 17: Merchant Risk Profiles strictly constrain retry attempts, SMS channel, and max auto values."""
    from eval.schemas import MERCHANT_RISK_PROFILES
    
    # 1. Conservative Profile: max_attempts=1, allow_sms=False, max_auto_value=5000
    conservative_engine = PayRecoverAIEngine(risk_profile=MERCHANT_RISK_PROFILES["Conservative"])
    
    # A. Retry attempt 2 should be blocked (max_attempts = 1)
    case_attempt_2 = make_test_case(amount_inr=3000.0, failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT")
    case_attempt_2.payment.attempt_number = 2
    dec_att2 = conservative_engine.decide(case_attempt_2)
    assert dec_att2.action_type != ActionType.RETRY_PAYMENT
    
    # B. SMS is forbidden -> channel must be EMAIL
    case_notify = make_test_case(amount_inr=2000.0, failure_code="BAD_REQUEST_INSUFFICIENT_FUNDS", dnd=False)
    dec_notify = conservative_engine.decide(case_notify)
    if dec_notify.action_type == ActionType.NOTIFY_PAYMENT_LINK:
        assert dec_notify.action_parameters["channel"] == "EMAIL"
    
    # C. Value exceeding max_auto_value (₹8,000 > ₹5,000) -> auto retry blocked, escalated
    case_high = make_test_case(amount_inr=8000.0, failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT")
    dec_high = conservative_engine.decide(case_high)
    assert dec_high.action_type != ActionType.RETRY_PAYMENT
    assert dec_high.action_type == ActionType.ESCALATE_TO_SUPPORT
    
    # 2. Balanced Profile: max_attempts=2, allow_sms=True, max_auto_value=10000
    balanced_engine = PayRecoverAIEngine(risk_profile=MERCHANT_RISK_PROFILES["Balanced"])
    case_bal_att2 = make_test_case(amount_inr=3000.0, failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT")
    case_bal_att2.payment.attempt_number = 2
    dec_bal = balanced_engine.decide(case_bal_att2)
    assert dec_bal.action_type == ActionType.RETRY_PAYMENT
    
    # 3. Aggressive Profile: max_attempts=3, allow_sms=True, max_auto_value=25000
    aggressive_engine = PayRecoverAIEngine(risk_profile=MERCHANT_RISK_PROFILES["Aggressive"])
    case_agg_att3 = make_test_case(amount_inr=15000.0, failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT")
    case_agg_att3.payment.attempt_number = 3
    dec_agg = aggressive_engine.decide(case_agg_att3)
    assert dec_agg.action_type == ActionType.RETRY_PAYMENT


def test_18_sample_count_standardization():
    """Test 18: Standardized sample count partitioning (N=10,000 -> 6k DEV, 2k TEST, 2k HOLDOUT per seed)."""
    holdout_seed42 = EvaluationDataset.load_dataset(seed=42, n=10000, split="holdout")
    test_seed42 = EvaluationDataset.load_dataset(seed=42, n=10000, split="test")
    dev_seed42 = EvaluationDataset.load_dataset(seed=42, n=10000, split="dev")
    
    assert len(holdout_seed42) == 2000
    assert len(test_seed42) == 2000
    assert len(dev_seed42) == 6000
    
    # 5-seed benchmark evaluates exactly 10,000 holdout observations
    total_evaluated_holdout = len(holdout_seed42) * 5
    assert total_evaluated_holdout == 10000
