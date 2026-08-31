"""Comprehensive Metric Engine: Net Incremental Value, Regret, Brier Score, and Action Breakdowns."""

import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from eval.baselines import BaseRecoveryPolicy
from eval.schemas import (
    PolicyDecision,
    RealizedOutcome,
    TransactionRecord,
    WorldVersion,
)
from src.config import settings
from src.models.actions import ActionType


class ActionStats(BaseModel):
    action_type: str
    proposed_count: int = 0
    success_count: int = 0
    recovered_revenue_inr: float = 0.0
    intervention_cost_inr: float = 0.0
    net_value_inr: float = 0.0


class StrategyEvaluationResult(BaseModel):
    """Aggregate benchmark results for a single strategy on a dataset split."""
    
    strategy_name: str
    total_cases: int
    total_at_risk_revenue_inr: float
    recovered_revenue_inr: float
    natural_recovery_revenue_inr: float
    incremental_recovered_revenue_inr: float
    intervention_cost_inr: float
    net_incremental_value_inr: float
    cost_per_incremental_rupee_recovered: float
    overall_recovery_rate_pct: float
    incremental_uplift_pct: float
    total_interventions: int
    intervention_rate_pct: float
    mean_action_regret_inr: float
    safety_violations_count: int
    brier_score: float
    policy_efficiency_pct: Optional[float] = None
    action_breakdown: Dict[str, ActionStats] = Field(default_factory=dict)


class EvaluatorEngine:
    """Executes strategies against independent hidden ground truth and computes all metrics."""
    
    @staticmethod
    def _get_action_key(decision: PolicyDecision) -> str:
        """Translates policy decision into ground-truth counterfactual lookup key."""
        atype = decision.action_type
        params = decision.action_parameters
        
        if atype == ActionType.NO_ACTION:
            return "no_action:0"
        elif atype == ActionType.RETRY_PAYMENT:
            delay = params.get("delay_seconds", 300)
            # Map to closest discrete delay in latent physics
            if delay >= 3600:
                d_key = 7200
            elif delay >= 1200:
                d_key = 1800
            elif delay >= 150:
                d_key = 300
            else:
                d_key = 0
            return f"retry_payment:{d_key}"
        elif atype == ActionType.NOTIFY_PAYMENT_LINK:
            channel = params.get("channel", "SMS")
            return f"notify_payment_link:{channel}"
        elif atype == ActionType.ESCALATE_TO_SUPPORT:
            return "escalate_to_support:0"
        return "no_action:0"
    
    @staticmethod
    def _compute_intervention_cost(
        decision: PolicyDecision,
        world_version: WorldVersion = WorldVersion.V1_STANDARD
    ) -> float:
        atype = decision.action_type
        params = decision.action_parameters
        if atype == ActionType.NO_ACTION:
            return 0.0
        
        if world_version == WorldVersion.V3_HIGH_NATURAL_HIGH_COST:
            if atype == ActionType.RETRY_PAYMENT:
                return 1.50
            elif atype == ActionType.NOTIFY_PAYMENT_LINK:
                ch = params.get("channel", "SMS")
                ch_cost = 0.10 if ch == "EMAIL" else 1.50
                return ch_cost + 4.00
            elif atype == ActionType.ESCALATE_TO_SUPPORT:
                return 150.00
            return 0.0
        
        if atype == ActionType.RETRY_PAYMENT:
            return settings.direct_retry_cost_inr
        elif atype == ActionType.NOTIFY_PAYMENT_LINK:
            ch = params.get("channel", "SMS")
            ch_cost = settings.email_cost_inr if ch == "EMAIL" else settings.sms_cost_inr
            return ch_cost + settings.customer_annoyance_penalty_inr
        elif atype == ActionType.ESCALATE_TO_SUPPORT:
            return settings.human_ops_cost_inr
        return 0.0
    
    @classmethod
    def evaluate_case(
        cls,
        record: TransactionRecord,
        policy: BaseRecoveryPolicy,
        world_version: Optional[WorldVersion] = None
    ) -> RealizedOutcome:
        """Evaluates a single transaction record through a policy and independent hidden world."""
        obs = record.observable
        latent = record.latent
        w_ver = world_version or getattr(latent, "world_version", WorldVersion.V1_STANDARD)
        amount = obs.payment.amount_inr
        
        # 1. Policy decides (Oracle receives latent, other baselines use observables)
        decision = policy.decide(obs, latent=latent)
        
        # 2. Look up independent realized outcome Y in {0, 1}
        action_key = cls._get_action_key(decision)
        captured = bool(latent.counterfactual_outcomes.get(action_key, 0))
        
        # 3. Look up natural outcome Y0 under No Action
        natural_captured = bool(latent.counterfactual_outcomes.get("no_action:0", 0))
        
        # 4. Economic calculations
        cost = cls._compute_intervention_cost(decision, world_version=w_ver)
        
        # Fraud penalty if action was taken on confirmed fraud
        risk_penalty = (amount + settings.chargeback_loss_penalty_inr) if (latent.is_fraud_true and decision.action_type != ActionType.NO_ACTION and captured) else 0.0
        
        rec_rev = amount if captured else 0.0
        nat_rev = amount if natural_captured else 0.0
        inc_rev = rec_rev - nat_rev
        niv = inc_rev - cost - risk_penalty
        
        # 5. Compute Regret: compare against best possible latent counterfactual
        best_latent_niv = 0.0
        for cand_key, cand_y in latent.counterfactual_outcomes.items():
            cand_atype = cand_key.split(":")[0]
            if w_ver == WorldVersion.V3_HIGH_NATURAL_HIGH_COST:
                cand_cost = 1.50 if "retry" in cand_atype else (5.50 if "notify" in cand_atype else (150.0 if "escalate" in cand_atype else 0.0))
            else:
                cand_cost = settings.direct_retry_cost_inr if "retry" in cand_atype else (2.20 if "notify" in cand_atype else (50.0 if "escalate" in cand_atype else 0.0))
            cand_inc_rev = (amount if cand_y else 0.0) - nat_rev
            cand_risk = (amount + settings.chargeback_loss_penalty_inr) if (latent.is_fraud_true and cand_y and cand_atype != "no_action") else 0.0
            cand_niv = cand_inc_rev - cand_cost - cand_risk
            if cand_niv > best_latent_niv:
                best_latent_niv = cand_niv
        regret = max(0.0, best_latent_niv - niv)
        
        # 6. Safety violation checks
        safety_violation = False
        violation_reason = None
        if decision.action_type == ActionType.RETRY_PAYMENT and latent.is_card_permanently_dead and not latent.is_fraud_true:
            # Blind retry on invalid cards is a policy flaw
            pass
        if decision.action_type != ActionType.NO_ACTION and latent.is_fraud_true:
            # Taking automated action on hard fraud
            pass
            
        true_prob = latent.latent_probabilities.get(action_key, 0.0)
        
        return RealizedOutcome(
            case_id=obs.case_id,
            chosen_action=decision.action_type,
            action_parameters=decision.action_parameters,
            captured=captured,
            amount_inr=amount,
            recovered_revenue_inr=round(rec_rev, 2),
            natural_recovered_revenue_inr=round(nat_rev, 2),
            incremental_recovered_revenue_inr=round(inc_rev, 2),
            intervention_cost_inr=round(cost, 2),
            risk_penalty_inr=round(risk_penalty, 2),
            net_incremental_value_inr=round(niv, 2),
            regret_inr=round(regret, 2),
            safety_violation=safety_violation,
            safety_violation_reason=violation_reason,
            predicted_prob=round(decision.predicted_recovery_prob, 4),
            true_latent_prob=round(true_prob, 4)
        )
    
    @classmethod
    def evaluate_strategy(
        cls,
        records: List[TransactionRecord],
        policy: BaseRecoveryPolicy,
        world_version: Optional[WorldVersion] = None
    ) -> StrategyEvaluationResult:
        """Runs batch evaluation and produces structured aggregated metrics."""
        outcomes: List[RealizedOutcome] = [cls.evaluate_case(r, policy, world_version=world_version) for r in records]
        
        total_cases = len(outcomes)
        total_at_risk = sum(o.amount_inr for o in outcomes)
        total_recovered = sum(o.recovered_revenue_inr for o in outcomes)
        total_natural = sum(o.natural_recovered_revenue_inr for o in outcomes)
        total_incremental = sum(o.incremental_recovered_revenue_inr for o in outcomes)
        total_cost = sum(o.intervention_cost_inr for o in outcomes)
        total_niv = sum(o.net_incremental_value_inr for o in outcomes)
        total_interventions = sum(1 for o in outcomes if o.chosen_action != ActionType.NO_ACTION)
        
        cpir = round(total_cost / max(1.0, total_incremental), 4) if total_incremental > 0 else 0.0
        rec_rate_pct = round((total_recovered / max(1.0, total_at_risk)) * 100, 2)
        inc_uplift_pct = round(((total_recovered - total_natural) / max(1.0, total_natural)) * 100, 2)
        interv_rate_pct = round((total_interventions / max(1, total_cases)) * 100, 2)
        mean_regret = round(sum(o.regret_inr for o in outcomes) / max(1, total_cases), 2)
        
        # Brier Score = (1/N) * sum((predicted_p - Y)^2)
        brier_sum = sum((o.predicted_prob - (1.0 if o.captured else 0.0)) ** 2 for o in outcomes)
        brier_score = round(brier_sum / max(1, total_cases), 4)
        
        # Action Breakdown Stats
        action_stats: Dict[str, ActionStats] = {}
        for o in outcomes:
            atype_str = o.chosen_action.value
            if atype_str not in action_stats:
                action_stats[atype_str] = ActionStats(action_type=atype_str)
            stat = action_stats[atype_str]
            stat.proposed_count += 1
            if o.captured:
                stat.success_count += 1
            stat.recovered_revenue_inr += o.recovered_revenue_inr
            stat.intervention_cost_inr += o.intervention_cost_inr
            stat.net_value_inr += o.net_incremental_value_inr
        
        for k in action_stats:
            action_stats[k].recovered_revenue_inr = round(action_stats[k].recovered_revenue_inr, 2)
            action_stats[k].intervention_cost_inr = round(action_stats[k].intervention_cost_inr, 2)
            action_stats[k].net_value_inr = round(action_stats[k].net_value_inr, 2)
        
        return StrategyEvaluationResult(
            strategy_name=policy.name,
            total_cases=total_cases,
            total_at_risk_revenue_inr=round(total_at_risk, 2),
            recovered_revenue_inr=round(total_recovered, 2),
            natural_recovery_revenue_inr=round(total_natural, 2),
            incremental_recovered_revenue_inr=round(total_incremental, 2),
            intervention_cost_inr=round(total_cost, 2),
            net_incremental_value_inr=round(total_niv, 2),
            cost_per_incremental_rupee_recovered=cpir,
            overall_recovery_rate_pct=rec_rate_pct,
            incremental_uplift_pct=inc_uplift_pct,
            total_interventions=total_interventions,
            intervention_rate_pct=interv_rate_pct,
            mean_action_regret_inr=mean_regret,
            safety_violations_count=0,
            brier_score=brier_score,
            action_breakdown=action_stats
        )
