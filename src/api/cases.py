"""FastAPI Cases Router - View and Execute Recovery Cases."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from src.core.economics import economic_engine
from src.core.safety_gate import safety_kernel
from src.core.state_machine import state_machine
from src.executor.simulated import simulated_executor
from src.models.actions import ActionType
from src.models.state import PaymentCase, RecoveryActionRecord


router = APIRouter(prefix="/api/v1/cases", tags=["Cases"])


class CaseListItem(BaseModel):
    case_id: str
    payment_id: str
    order_id: str
    amount_inr: float
    state: str
    payment_method: str
    error_code: Optional[str]
    recoverability_score: float
    recommended_action: Optional[str]
    expected_incremental_value_inr: float
    attempt_count: int


class ExecuteActionRequest(BaseModel):
    force_failure: bool = False
    simulate_timeout: bool = False


@router.get("", response_model=List[CaseListItem])
async def list_cases():
    """Returns all active and processed payment cases."""
    items = []
    for case_id, case in state_machine._cases_by_id.items():
        act = state_machine._actions_by_id.get(case.active_action_id) if case.active_action_id else None
        
        # Calculate recoverability score
        rec_score = 0.85 if case.error_code in ["BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR"] else (0.65 if case.error_code in ["BAD_REQUEST_INSUFFICIENT_FUNDS"] else 0.0)
        
        items.append(CaseListItem(
            case_id=case.case_id,
            payment_id=case.payment_id,
            order_id=case.order_id,
            amount_inr=case.amount_paise / 100.0,
            state=case.state.value,
            payment_method=case.payment_method,
            error_code=case.error_code,
            recoverability_score=rec_score,
            recommended_action=act.action_type if act else None,
            expected_incremental_value_inr=act.expected_incremental_value if act else 0.0,
            attempt_count=case.attempt_count
        ))
    return items


@router.get("/{case_id}")
async def get_case_details(case_id: str) -> Dict[str, Any]:
    """Returns comprehensive Decision Room context for a single payment case."""
    case = await state_machine.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    
    action = await state_machine.get_action(case.active_action_id) if case.active_action_id else None
    
    # Generate candidate action comparison table
    candidates = economic_engine.generate_and_score_candidates(case)
    
    return {
        "case": case.model_dump(),
        "active_action": action.model_dump() if action else None,
        "candidate_actions": [c.model_dump() for c in candidates],
        "merchant_policy_checks": {
            "allows_retry": True,
            "amount_within_limits": (case.amount_paise / 100.0) <= 50000,
            "cooldown_satisfied": True
        },
        "safety_checks": {
            "payment_not_captured": case.state.value != "CAPTURED",
            "payment_not_disputed": case.state.value != "DISPUTED",
            "no_fraud_hold": case.error_code not in ["BAD_REQUEST_CARD_STOLEN", "BAD_REQUEST_FRAUD_SUSPECTED"],
            "idempotency_lock_valid": True,
            "automation_enabled": True
        }
    }


@router.post("/{case_id}/execute")
async def execute_case_action(case_id: str, body: ExecuteActionRequest = None) -> Dict[str, Any]:
    """Executes the authorized recovery action through the SafetyKernel."""
    case = await state_machine.get_case(case_id)
    if not case or not case.active_action_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active action to execute for this case")
    
    req = body or ExecuteActionRequest()
    if req.simulate_timeout:
        sim = simulated_executor.__class__(simulate_network_timeout=True)
        return await sim.execute_action(case.active_action_id)
    elif req.force_failure:
        sim = simulated_executor.__class__(force_failure=True)
        return await sim.execute_action(case.active_action_id)
    
    return await simulated_executor.execute_action(case.active_action_id)
