"""Idempotent Simulated Razorpay Action Executor."""

from datetime import datetime, timezone
from typing import Any, Dict
from src.core.audit import AuditEventType, audit_ledger
from src.core.safety_gate import safety_kernel
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.models.actions import ActionType
from src.models.state import ActionStatus, PaymentCase, PaymentState, RecoveryActionRecord


class SimulatedExecutor:
    """Dispatches authorized recovery interventions and updates case lifecycle."""
    
    def __init__(self, simulate_network_timeout: bool = False, force_failure: bool = False):
        self.simulate_network_timeout = simulate_network_timeout
        self.force_failure = force_failure
    
    async def execute_action(
        self,
        action_id: str,
        raw_decision_dict: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Runs safety gate validation and executes the authorized action."""
        
        # 1. Authorize via 8-Stage Deterministic Safety Kernel
        auth_result = await safety_kernel.validate_and_authorize(
            action_id=action_id,
            raw_decision_dict=raw_decision_dict
        )
        
        if not auth_result.authorized:
            return {
                "success": False,
                "status": "BLOCKED_BY_SAFETY_KERNEL",
                "reason": auth_result.reason
            }
        
        action = auth_result.action
        case = await state_machine.get_case(action.case_id)
        
        await state_machine.update_action_status(action.action_id, ActionStatus.EXECUTING)
        await state_machine.update_case_state(case.case_id, PaymentState.EXECUTING)
        
        # 2. Simulate HTTP 504 Gateway Timeout Handling (SS-10)
        if self.simulate_network_timeout:
            await telemetry.increment("partial_execution_count")
            await state_machine.update_action_status(action.action_id, ActionStatus.FAILED, outcome="GATEWAY_504_TIMEOUT")
            await audit_ledger.record_event(
                AuditEventType.ACTION_EXECUTED,
                {"action_id": action.action_id, "status": "GATEWAY_TIMEOUT_FAIL_SAFE", "idempotency_key": action.idempotency_key},
                case_id=case.case_id,
                payment_id=case.payment_id
            )
            return {
                "success": False,
                "status": "GATEWAY_TIMEOUT",
                "reason": "HTTP 504 received. State kept in pending reconciliation without duplicate retry."
            }
        
        # 3. Action Type Execution Branching
        if action.action_type == ActionType.RETRY_PAYMENT.value:
            case.attempt_count += 1
            case.last_attempt_at = datetime.now(timezone.utc)
            
            if self.force_failure:
                await state_machine.update_action_status(action.action_id, ActionStatus.FAILED, outcome="PAYMENT_DECLINED")
                await state_machine.update_case_state(case.case_id, PaymentState.OBSERVED_FAILED)
                outcome_status = "RETRY_FAILED"
                final_case_state = PaymentState.OBSERVED_FAILED
            else:
                # Simulated capture success
                await state_machine.update_action_status(action.action_id, ActionStatus.SUCCEEDED, outcome="PAYMENT_CAPTURED")
                await state_machine.update_case_state(case.case_id, PaymentState.CAPTURED)
                outcome_status = "PAYMENT_CAPTURED"
                final_case_state = PaymentState.CAPTURED
        
        elif action.action_type == ActionType.NOTIFY_PAYMENT_LINK.value:
            case.notification_count += 1
            await state_machine.update_action_status(action.action_id, ActionStatus.SUCCEEDED, outcome="LINK_DISPATCHED")
            await state_machine.update_case_state(case.case_id, PaymentState.SCHEDULED)
            outcome_status = "LINK_DISPATCHED"
            final_case_state = PaymentState.SCHEDULED
            
        elif action.action_type == ActionType.ESCALATE_TO_SUPPORT.value:
            await state_machine.update_action_status(action.action_id, ActionStatus.SUCCEEDED, outcome="ESCALATED")
            await state_machine.update_case_state(case.case_id, PaymentState.ESCALATED)
            outcome_status = "ESCALATED_TO_SUPPORT"
            final_case_state = PaymentState.ESCALATED
            
        else:  # NO_ACTION
            await state_machine.update_action_status(action.action_id, ActionStatus.SUCCEEDED, outcome="NO_ACTION_TAKEN")
            await state_machine.update_case_state(case.case_id, PaymentState.CLOSED)
            outcome_status = "CLOSED_NO_ACTION"
            final_case_state = PaymentState.CLOSED
        
        # 4. Commit Audit Event
        await audit_ledger.record_event(
            AuditEventType.ACTION_EXECUTED,
            {
                "action_id": action.action_id,
                "action_type": action.action_type,
                "idempotency_key": action.idempotency_key,
                "outcome_status": outcome_status,
                "final_case_state": final_case_state.value
            },
            case_id=case.case_id,
            payment_id=case.payment_id
        )
        
        return {
            "success": True,
            "status": outcome_status,
            "action_id": action.action_id,
            "case_id": case.case_id,
            "payment_state": final_case_state.value
        }


simulated_executor = SimulatedExecutor()
